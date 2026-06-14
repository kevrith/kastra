import hashlib
import logging
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select, text
from sqlalchemy.orm import selectinload

from app.database import AsyncSessionLocal, engine
from app.models.affiliate import Affiliate, AffiliateCommission, AffiliateReferral
from app.models.invoice import Invoice, InvoiceItem
from app.models.organization import Organization
from app.models.quotation import Quotation
from app.models.recurring_invoice import RecurringInvoice
from app.services.email_service import (
    send_due_soon_reminder_email,
    send_overdue_reminder_email,
    send_subscription_renewal_reminder_email,
    send_subscription_downgraded_email,
)
from app.utils.plan_limits import PLAN_PRICES_KES
from app.services.sms_service import sms_due_soon, sms_overdue_reminder
from app.utils.id_generator import next_id

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler(timezone="Africa/Nairobi")

# Namespace for Postgres advisory locks so our keys can't collide with other
# tooling using advisory locks on the same database.
_LOCK_NAMESPACE = 0x4B415354  # "KAST"


def _lock_key(job_id: str) -> int:
    digest = hashlib.sha256(job_id.encode()).digest()
    return int.from_bytes(digest[:4], "big", signed=True)


def _locked(job_id: str, fn):
    """
    Wrap a job so only one instance/worker runs it at a time. Every worker
    fires the cron, but only the one that wins the Postgres advisory lock
    executes; the rest skip. The lock is session-scoped: held on a dedicated
    connection for the job's duration and auto-released if the process dies.
    """

    async def runner():
        key = _lock_key(job_id)
        async with engine.connect() as conn:
            got = (
                await conn.execute(
                    text("SELECT pg_try_advisory_lock(:ns, :key)"),
                    {"ns": _LOCK_NAMESPACE, "key": key},
                )
            ).scalar()
            if not got:
                logger.info("[scheduler] %s: another instance holds the lock — skipping.", job_id)
                return
            try:
                await fn()
            finally:
                await conn.execute(
                    text("SELECT pg_advisory_unlock(:ns, :key)"),
                    {"ns": _LOCK_NAMESPACE, "key": key},
                )

    runner.__name__ = f"locked_{fn.__name__}"
    return runner


"""
Smart reminder schedule (milestone-based, not daily spam):
  Milestone 0 → send 7 days BEFORE due date  (due-soon notice)
  Milestone 1 → send ON / just after due date  (1st overdue)
  Milestone 2 → send at 7 days overdue
  Milestone 3 → send at 30 days overdue
  Milestone 4 → send at 60 days overdue (final notice)

reminders_sent tracks how many milestones have fired.
last_reminded_at guards against double-sends on the same day.
"""
# Days-from-due-date at which each milestone fires (negative = before due)
_REMINDER_MILESTONES = [-7, 0, 7, 30, 60]
_MIN_GAP_HOURS = 20  # won't re-send within this many hours


async def _process_smart_reminders():
    now = datetime.now(timezone.utc)
    async with AsyncSessionLocal() as db:
        try:
            result = await db.execute(
                select(Invoice)
                .where(
                    Invoice.payment_status.in_(["unpaid", "partial"]),
                    Invoice.due_date.isnot(None),
                    Invoice.reminders_sent < len(_REMINDER_MILESTONES),
                )
                .options(
                    selectinload(Invoice.client),
                    selectinload(Invoice.organization),
                )
            )
            candidates = result.scalars().all()

            sent_count = 0
            for inv in candidates:
                # Skip if we already sent a reminder recently (prevents double-fires)
                if inv.last_reminded_at:
                    hours_since = (now - inv.last_reminded_at).total_seconds() / 3600
                    if hours_since < _MIN_GAP_HOURS:
                        continue

                milestone_day = _REMINDER_MILESTONES[inv.reminders_sent]
                days_from_due = (now.date() - inv.due_date.date()).days

                if days_from_due < milestone_day:
                    continue  # Not yet time for this milestone

                client_email = inv.client.email if inv.client else None
                client_name = inv.client.name if inv.client else "Client"
                biz_name = inv.organization.name if inv.organization else "Your supplier"
                balance_due = float(inv.grand_total) - float(inv.amount_paid or 0)

                try:
                    client_phone = inv.client.phone if inv.client else None
                    client_sms_consent = getattr(inv.client, "sms_consent", False) if inv.client else False
                    if milestone_day < 0:
                        # Pre-due: friendly heads-up
                        days_until = max(1, -days_from_due)
                        if client_email:
                            await send_due_soon_reminder_email(
                                client_email=client_email,
                                invoice_id=inv.id,
                                amount=balance_due,
                                business_name=biz_name,
                                days_until_due=days_until,
                            )
                        await sms_due_soon(
                            client_phone=client_phone,
                            client_name=client_name,
                            invoice_id=inv.id,
                            amount=balance_due,
                            business_name=biz_name,
                            days_until_due=days_until,
                            sms_consent=client_sms_consent,
                        )
                    else:
                        # Overdue reminder
                        days_overdue = max(0, days_from_due)
                        if client_email:
                            await send_overdue_reminder_email(
                                client_email=client_email,
                                invoice_id=inv.id,
                                amount=float(inv.grand_total),
                                business_name=biz_name,
                                days_overdue=days_overdue,
                                balance_due=balance_due,
                            )
                        await sms_overdue_reminder(
                            client_phone=client_phone,
                            client_name=client_name,
                            invoice_id=inv.id,
                            balance_due=balance_due,
                            business_name=biz_name,
                            days_overdue=days_overdue,
                            sms_consent=client_sms_consent,
                        )

                    inv.reminders_sent += 1
                    inv.last_reminded_at = now
                    sent_count += 1
                    logger.info(
                        "[scheduler] Reminder milestone %d sent for %s (%s days from due).",
                        inv.reminders_sent, inv.id, days_from_due,
                    )
                except Exception:
                    logger.exception("[scheduler] Failed to send reminder for %s", inv.id)

            await db.commit()
            logger.info("[scheduler] Smart reminders: %d sent.", sent_count)
        except Exception:
            logger.exception("[scheduler] Error in smart reminder job")
            await db.rollback()


async def _expire_quotations():
    """
    Nightly job — auto-moves draft/pending quotations past their expiry date to 'expired'.
    """
    now = datetime.now(timezone.utc)
    async with AsyncSessionLocal() as db:
        try:
            result = await db.execute(
                select(Quotation).where(
                    Quotation.status.in_(["draft", "pending"]),
                    Quotation.expires_at.isnot(None),
                    Quotation.expires_at < now,
                )
            )
            expired = result.scalars().all()

            if not expired:
                logger.info("[scheduler] No quotations to expire.")
                return

            for qt in expired:
                qt.status = "expired"

            await db.commit()
            logger.info("[scheduler] Expired %d quotation(s): %s", len(expired), [q.id for q in expired])
        except Exception:
            logger.exception("[scheduler] Error in quotation expiry job")
            await db.rollback()


_FREQ_DELTA = {
    "weekly": timedelta(weeks=1),
    "monthly": timedelta(days=30),
    "quarterly": timedelta(days=91),
    "yearly": timedelta(days=365),
}

VAT_RATE = Decimal("0.16")


async def _fire_recurring_invoices():
    """
    Daily job — creates invoices from active recurring templates whose next_run_at is due.
    """
    now = datetime.now(timezone.utc)
    async with AsyncSessionLocal() as db:
        try:
            result = await db.execute(
                select(RecurringInvoice)
                .where(
                    RecurringInvoice.is_active.is_(True),
                    RecurringInvoice.next_run_at <= now,
                )
                .options(
                    selectinload(RecurringInvoice.organization),
                    selectinload(RecurringInvoice.client),
                )
            )
            due = result.scalars().all()

            if not due:
                logger.info("[scheduler] No recurring invoices due.")
                return

            for rec in due:
                try:
                    subtotal = sum(
                        Decimal(str(i["quantity"])) * Decimal(str(i["unit_price"]))
                        for i in rec.items
                    )
                    vat = (subtotal * VAT_RATE).quantize(Decimal("0.01"))
                    grand_total = subtotal + vat

                    inv_id = await next_id(db, "invoice", rec.organization_id)
                    invoice = Invoice(
                        id=inv_id,
                        organization_id=rec.organization_id,
                        client_id=rec.client_id,
                        subtotal=subtotal,
                        vat_amount=vat,
                        grand_total=grand_total,
                        due_date=now + timedelta(days=30),
                    )
                    db.add(invoice)

                    for idx, item in enumerate(rec.items):
                        line_total = Decimal(str(item["quantity"])) * Decimal(str(item["unit_price"]))
                        db.add(InvoiceItem(
                            invoice_id=inv_id,
                            description=item["description"],
                            quantity=Decimal(str(item["quantity"])),
                            unit_price=Decimal(str(item["unit_price"])),
                            line_total=line_total,
                            sort_order=idx,
                        ))

                    await db.flush()

                    delta = _FREQ_DELTA.get(rec.frequency, timedelta(days=30))
                    rec.last_run_at = now
                    rec.next_run_at = now + delta

                    logger.info("[scheduler] Created recurring invoice %s from template %s", inv_id, rec.id)
                except Exception:
                    logger.exception("[scheduler] Failed to process recurring invoice %s", rec.id)

            await db.commit()
        except Exception:
            logger.exception("[scheduler] Error in recurring invoice job")
            await db.rollback()


async def _expire_trials():
    """
    Nightly job — downgrades organisations whose free trial has ended to the free plan.
    """
    now = datetime.now(timezone.utc)
    async with AsyncSessionLocal() as db:
        try:
            result = await db.execute(
                select(Organization).where(
                    Organization.is_trial.is_(True),
                    Organization.trial_ends_at.isnot(None),
                    Organization.trial_ends_at < now,
                )
            )
            expired = result.scalars().all()
            if not expired:
                logger.info("[scheduler] No expired trials.")
                return
            for org in expired:
                old_plan = org.plan
                org.plan = "free"
                org.plan_status = "active"
                org.is_trial = False
                org.trial_ends_at = None
                org.next_billing_date = None
                logger.info("[scheduler] Trial expired: org=%s plan=%s → free", org.id, old_plan)
            await db.commit()
            logger.info("[scheduler] Expired %d trial(s).", len(expired))
        except Exception:
            logger.exception("[scheduler] Error in trial expiry job")
            await db.rollback()


async def _expire_complimentary():
    """
    Nightly job — revokes complimentary access when complimentary_ends_at has passed.
    Downgrades the org to free plan.
    """
    now = datetime.now(timezone.utc)
    async with AsyncSessionLocal() as db:
        try:
            result = await db.execute(
                select(Organization).where(
                    Organization.plan_status == "complimentary",
                    Organization.complimentary_ends_at.isnot(None),
                    Organization.complimentary_ends_at < now,
                )
            )
            expired = result.scalars().all()
            if not expired:
                logger.info("[scheduler] No expired complimentary accounts.")
                return
            for org in expired:
                old_plan = org.plan
                org.plan = "free"
                org.plan_status = "active"
                org.complimentary_ends_at = None
                org.complimentary_reason = None
                logger.info("[scheduler] Complimentary expired: org=%s plan=%s → free", org.id, old_plan)
            await db.commit()
            logger.info("[scheduler] Expired %d complimentary account(s).", len(expired))
        except Exception:
            logger.exception("[scheduler] Error in complimentary expiry job")
            await db.rollback()


async def _send_billing_reminders():
    """
    Nightly — sends a renewal reminder email exactly 5 days before next_billing_date.
    Fires once per billing cycle since it targets the exact day-5 window.
    """
    now = datetime.now(timezone.utc)
    target_date = (now + timedelta(days=5)).date()
    async with AsyncSessionLocal() as db:
        try:
            result = await db.execute(
                select(Organization)
                .where(
                    Organization.plan != "free",
                    Organization.plan_status == "active",
                    Organization.is_trial.is_(False),
                    Organization.next_billing_date.isnot(None),
                )
                .options(selectinload(Organization.users))
            )
            orgs = result.scalars().all()
            sent = 0
            for org in orgs:
                if not org.next_billing_date:
                    continue
                if org.next_billing_date.date() != target_date:
                    continue
                admin = next(
                    (u for u in org.users if u.role == "admin" and u.is_active), None
                )
                if not admin:
                    continue
                price = PLAN_PRICES_KES.get(org.plan, 0)
                try:
                    await send_subscription_renewal_reminder_email(
                        admin.email, org.name, org.plan, price, org.next_billing_date
                    )
                    sent += 1
                    logger.info("[scheduler] Billing reminder sent: org=%s plan=%s due=%s", org.id, org.plan, org.next_billing_date.date())
                except Exception:
                    logger.exception("[scheduler] Failed to send billing reminder for org=%s", org.id)
            logger.info("[scheduler] Billing reminders sent: %d.", sent)
        except Exception:
            logger.exception("[scheduler] Error in billing reminder job")


async def _expire_subscriptions():
    """
    Nightly — auto-downgrades paid orgs that are more than 3 days past their next_billing_date
    without having renewed. Sends a downgrade notification email to the org admin.
    """
    now = datetime.now(timezone.utc)
    grace_cutoff = now - timedelta(days=3)
    async with AsyncSessionLocal() as db:
        try:
            result = await db.execute(
                select(Organization)
                .where(
                    Organization.plan != "free",
                    Organization.plan_status == "active",
                    Organization.is_trial.is_(False),
                    Organization.next_billing_date.isnot(None),
                    Organization.next_billing_date < grace_cutoff,
                )
                .options(selectinload(Organization.users))
            )
            expired = result.scalars().all()
            if not expired:
                logger.info("[scheduler] No subscriptions to expire.")
                return
            for org in expired:
                old_plan = org.plan
                org.plan = "free"
                org.plan_status = "active"
                org.billing_cycle_start = None
                org.next_billing_date = None
                logger.info("[scheduler] Subscription expired: org=%s plan=%s → free", org.id, old_plan)
                admin = next(
                    (u for u in org.users if u.role == "admin" and u.is_active), None
                )
                if admin:
                    try:
                        await send_subscription_downgraded_email(admin.email, org.name, old_plan)
                    except Exception:
                        logger.exception("[scheduler] Failed to send downgrade email for org=%s", org.id)
            await db.commit()
            logger.info("[scheduler] Expired %d subscription(s).", len(expired))
        except Exception:
            logger.exception("[scheduler] Error in subscription expiry job")
            await db.rollback()


async def _reset_monthly_counters():
    """
    Nightly job — resets invoice/quotation/OCR counters for any org whose
    billing cycle rolled over into a new calendar month.
    """
    now = datetime.now(timezone.utc)
    async with AsyncSessionLocal() as db:
        try:
            result = await db.execute(select(Organization))
            orgs = result.scalars().all()
            reset_count = 0
            for org in orgs:
                reset_at = org.counters_reset_at
                if reset_at is None or (now.year > reset_at.year or now.month > reset_at.month):
                    org.invoices_this_month = 0
                    org.quotations_this_month = 0
                    org.ocr_scans_this_month = 0
                    org.ai_calls_this_month = 0
                    org.counters_reset_at = now
                    reset_count += 1
            await db.commit()
            logger.info("[scheduler] Monthly counters reset for %d org(s).", reset_count)
        except Exception:
            logger.exception("[scheduler] Error in monthly counter reset job")
            await db.rollback()


async def _credit_affiliate_commissions():
    """
    Runs on the 1st of each month — credits KSh commission to each active affiliate
    for every referred organisation that is on a paid (non-trial) plan.
    Uses the previous calendar month as the billing period.
    """
    from app.config import settings as _settings
    now = datetime.now(timezone.utc)
    # Derive previous month label e.g. "2026-05"
    if now.month == 1:
        prev_month = f"{now.year - 1}-12"
    else:
        prev_month = f"{now.year}-{now.month - 1:02d}"

    async with AsyncSessionLocal() as db:
        try:
            referrals = (await db.execute(
                select(AffiliateReferral)
                .options(selectinload(AffiliateReferral.organization))
            )).scalars().all()

            credited = 0
            for ref in referrals:
                org = ref.organization
                if org.plan == "free" or org.is_trial:
                    continue

                # Skip if already credited this month
                exists = (await db.execute(
                    select(AffiliateCommission).where(
                        AffiliateCommission.affiliate_id == ref.affiliate_id,
                        AffiliateCommission.organization_id == ref.organization_id,
                        AffiliateCommission.month == prev_month,
                    )
                )).scalar_one_or_none()
                if exists:
                    continue

                amount = Decimal(str(_settings.affiliate_commission_ksh))
                db.add(AffiliateCommission(
                    affiliate_id=ref.affiliate_id,
                    organization_id=ref.organization_id,
                    month=prev_month,
                    amount_ksh=amount,
                ))

                aff = (await db.execute(
                    select(Affiliate).where(Affiliate.id == ref.affiliate_id)
                )).scalar_one_or_none()
                if aff:
                    aff.balance_ksh = Decimal(str(aff.balance_ksh)) + amount
                    aff.total_earned_ksh = Decimal(str(aff.total_earned_ksh)) + amount
                    credited += 1

            await db.commit()
            logger.info("[scheduler] Affiliate commissions credited: %d entries for month %s.", credited, prev_month)
        except Exception:
            logger.exception("[scheduler] Error in affiliate commission job")
            await db.rollback()


async def _auto_payout_affiliates():
    """
    Runs on the 1st of each month, just after commissions are credited.
    Automatically pays out every active affiliate whose balance is at or above
    the minimum, via the same Paystack transfer path as manual withdrawals.

    Before paying, it checks the Paystack balance: if it can't cover everyone,
    it pays the affiliates that fit (oldest first), skips the rest so they roll
    over, and emails the admin to top up — so we never fire a wave of doomed
    transfers. Each affiliate is committed independently so one failed transfer
    can't roll back the rest of the batch.
    """
    from app.config import settings as _settings
    from app.routers.affiliate import execute_payout, _paystack_balance_ksh
    from app.services.email_service import send_affiliate_payout_shortfall_email

    min_payout = _settings.affiliate_min_payout_ksh
    async with AsyncSessionLocal() as db:
        affiliates = (await db.execute(
            select(Affiliate).where(
                Affiliate.status == "active",
                Affiliate.balance_ksh >= min_payout,
            ).order_by(Affiliate.created_at)
        )).scalars().all()

        if not affiliates:
            logger.info("[scheduler] Auto affiliate payouts: no eligible affiliates.")
            return

        total_needed = sum(float(a.balance_ksh) for a in affiliates)
        # None means the balance couldn't be read — fall back to paying through and
        # letting per-transfer failure handling cover any shortfall.
        available = await _paystack_balance_ksh(_settings.paystack_secret_key)
        if available is not None and available < total_needed:
            logger.warning(
                "[scheduler] Paystack balance KSh %.0f < needed KSh %.0f for %d affiliates — paying what fits.",
                available, total_needed, len(affiliates),
            )
            try:
                await send_affiliate_payout_shortfall_email(total_needed, available, len(affiliates))
            except Exception:
                logger.exception("[scheduler] Failed to send payout shortfall alert")

        remaining = available  # budget tracker; None disables the budget gate
        paid = 0
        skipped = 0
        for aff in affiliates:
            amount = float(aff.balance_ksh)  # pay out the full available balance
            if remaining is not None and amount > remaining:
                skipped += 1
                continue
            try:
                payout = await execute_payout(aff, amount, db, method="auto")
                await db.commit()
                if payout.status == "processing":
                    paid += 1
                    if remaining is not None:
                        remaining -= amount
            except Exception:
                logger.exception("[scheduler] Auto payout failed for affiliate %s", aff.id)
                await db.rollback()
        logger.info("[scheduler] Auto affiliate payouts: %d transfers initiated, %d skipped (insufficient balance).", paid, skipped)


def start_scheduler():
    # Run jobs daily at midnight EAT (21:00 UTC). Every job is wrapped in a
    # Postgres advisory lock so running multiple workers/instances never
    # double-fires reminders, counter resets, or commission credits.
    _jobs = [
        ("smart_reminders", _process_smart_reminders, {"hour": 21, "minute": 0}),
        ("expire_quotations", _expire_quotations, {"hour": 21, "minute": 5}),
        ("recurring_invoices", _fire_recurring_invoices, {"hour": 21, "minute": 10}),
        ("reset_monthly_counters", _reset_monthly_counters, {"hour": 21, "minute": 15}),
        ("expire_trials", _expire_trials, {"hour": 21, "minute": 20}),
        ("expire_complimentary", _expire_complimentary, {"hour": 21, "minute": 25}),
        ("billing_reminders", _send_billing_reminders, {"hour": 21, "minute": 30}),
        ("expire_subscriptions", _expire_subscriptions, {"hour": 21, "minute": 35}),
        # Affiliate commissions — runs on the 1st of each month at 00:40 EAT (21:40 UTC)
        ("affiliate_commissions", _credit_affiliate_commissions, {"day": 1, "hour": 21, "minute": 40}),
        # Affiliate auto-payout — 10 min after commissions are credited, same day
        ("affiliate_auto_payout", _auto_payout_affiliates, {"day": 1, "hour": 21, "minute": 50}),
    ]
    for job_id, fn, cron in _jobs:
        scheduler.add_job(_locked(job_id, fn), "cron", id=job_id, **cron)
    scheduler.start()
    logger.info("[scheduler] Started. Jobs run daily at 00:00 EAT.")


def stop_scheduler():
    scheduler.shutdown(wait=False)
    logger.info("[scheduler] Stopped.")
