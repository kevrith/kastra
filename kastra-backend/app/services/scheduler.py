import logging
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.database import AsyncSessionLocal
from app.models.invoice import Invoice, InvoiceItem
from app.models.organization import Organization
from app.models.quotation import Quotation
from app.models.recurring_invoice import RecurringInvoice
from app.services.email_service import send_due_soon_reminder_email, send_overdue_reminder_email
from app.utils.id_generator import next_id

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler(timezone="Africa/Nairobi")


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
                    if milestone_day < 0:
                        # Pre-due: friendly heads-up
                        days_until = abs(days_from_due - milestone_day)
                        if client_email:
                            await send_due_soon_reminder_email(
                                client_email=client_email,
                                invoice_id=inv.id,
                                amount=balance_due,
                                business_name=biz_name,
                                days_until_due=max(1, -days_from_due),
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
                    org.counters_reset_at = now
                    reset_count += 1
            await db.commit()
            logger.info("[scheduler] Monthly counters reset for %d org(s).", reset_count)
        except Exception:
            logger.exception("[scheduler] Error in monthly counter reset job")
            await db.rollback()


def start_scheduler():
    # Run jobs daily at midnight EAT (21:00 UTC)
    scheduler.add_job(_process_smart_reminders, "cron", hour=21, minute=0, id="smart_reminders")
    scheduler.add_job(_expire_quotations, "cron", hour=21, minute=5, id="expire_quotations")
    scheduler.add_job(_fire_recurring_invoices, "cron", hour=21, minute=10, id="recurring_invoices")
    scheduler.add_job(_reset_monthly_counters, "cron", hour=21, minute=15, id="reset_monthly_counters")
    scheduler.add_job(_expire_trials, "cron", hour=21, minute=20, id="expire_trials")
    scheduler.add_job(_expire_complimentary, "cron", hour=21, minute=25, id="expire_complimentary")
    scheduler.start()
    logger.info("[scheduler] Started. Jobs run daily at 00:00 EAT.")


def stop_scheduler():
    scheduler.shutdown(wait=False)
    logger.info("[scheduler] Stopped.")
