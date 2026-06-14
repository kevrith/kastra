import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Affiliate(Base):
    __tablename__ = "affiliates"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    phone: Mapped[str] = mapped_column(String(20), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(200), nullable=False)
    code: Mapped[str] = mapped_column(String(20), nullable=False, unique=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")  # pending|active|suspended

    # Payout details
    payout_phone: Mapped[str] = mapped_column(String(20), nullable=False)  # M-Pesa number for payouts
    paystack_recipient_code: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Earnings
    balance_ksh: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=Decimal("0"))
    total_earned_ksh: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=Decimal("0"))
    total_paid_ksh: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=Decimal("0"))

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    referrals: Mapped[list["AffiliateReferral"]] = relationship(back_populates="affiliate")
    commissions: Mapped[list["AffiliateCommission"]] = relationship(back_populates="affiliate")
    payouts: Mapped[list["AffiliatePayout"]] = relationship(back_populates="affiliate")


class AffiliateReferral(Base):
    __tablename__ = "affiliate_referrals"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    affiliate_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("affiliates.id"), nullable=False)
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    affiliate: Mapped["Affiliate"] = relationship(back_populates="referrals")
    organization: Mapped["Organization"] = relationship()  # noqa: F821


class AffiliateCommission(Base):
    __tablename__ = "affiliate_commissions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    affiliate_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("affiliates.id"), nullable=False)
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    month: Mapped[str] = mapped_column(String(7), nullable=False)  # "2026-06"
    amount_ksh: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    affiliate: Mapped["Affiliate"] = relationship(back_populates="commissions")


class AffiliatePayout(Base):
    __tablename__ = "affiliate_payouts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    affiliate_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("affiliates.id"), nullable=False)
    amount_ksh: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    payout_phone: Mapped[str] = mapped_column(String(20), nullable=False)
    paystack_transfer_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    paystack_reference: Mapped[str | None] = mapped_column(String(100), nullable=True)
    method: Mapped[str] = mapped_column(String(10), nullable=False, default="manual")  # manual|auto
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")  # pending|processing|completed|failed
    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    affiliate: Mapped["Affiliate"] = relationship(back_populates="payouts")
