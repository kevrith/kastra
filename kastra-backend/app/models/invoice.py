import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Invoice(Base):
    __tablename__ = "invoices"
    __table_args__ = (
        Index("ix_invoices_organization_id", "organization_id"),
        Index("ix_invoices_client_id", "client_id"),
        Index("ix_invoices_payment_status", "payment_status"),
        Index("ix_invoices_created_at", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(20), primary_key=True)  # INV-YYYY-XXX
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    quotation_id: Mapped[str | None] = mapped_column(String(20), ForeignKey("quotations.id"), nullable=True)
    client_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("clients.id"), nullable=False)
    payment_status: Mapped[str] = mapped_column(String(20), nullable=False, default="unpaid")  # unpaid | partial | paid
    payment_method: Mapped[str | None] = mapped_column(String(30), nullable=True)  # mpesa | bank | cash
    subtotal: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False, default=0)
    vat_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False, default=0)
    grand_total: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False, default=0)
    due_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    lpo_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    discount_pct: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False, default=0)
    total_discount: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False, default=0)
    charges_total: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False, default=0)
    wht_pct: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False, default=0)
    wht_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False, default=0)
    deposit_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False, default=0)
    mpesa_checkout_request_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    amount_paid: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False, default=0)
    reminders_sent: Mapped[int] = mapped_column(Integer, default=0)
    last_reminded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # eTIMS / KRA
    etims_cu_invoice_no: Mapped[str | None] = mapped_column(String(50), nullable=True)
    etims_rcpt_sign: Mapped[str | None] = mapped_column(Text, nullable=True)
    etims_int_data: Mapped[str | None] = mapped_column(Text, nullable=True)
    etims_submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    organization: Mapped["Organization"] = relationship(back_populates="invoices")  # noqa: F821
    client: Mapped["Client"] = relationship(back_populates="invoices")  # noqa: F821
    quotation: Mapped["Quotation | None"] = relationship(  # noqa: F821
        foreign_keys=[quotation_id],
        primaryjoin="Invoice.quotation_id == Quotation.id",
    )
    items: Mapped[list["InvoiceItem"]] = relationship(
        back_populates="invoice", cascade="all, delete-orphan", order_by="InvoiceItem.sort_order"
    )
    charges: Mapped[list["InvoiceCharge"]] = relationship(
        back_populates="invoice", cascade="all, delete-orphan", order_by="InvoiceCharge.sort_order"
    )
    payment_detail: Mapped["PaymentDetail | None"] = relationship(
        back_populates="invoice", cascade="all, delete-orphan", uselist=False
    )
    payments: Mapped[list["InvoicePayment"]] = relationship(  # noqa: F821
        back_populates="invoice", cascade="all, delete-orphan", order_by="InvoicePayment.paid_at"
    )


class InvoiceItem(Base):
    __tablename__ = "invoice_items"
    __table_args__ = (
        Index("ix_invoice_items_invoice_id", "invoice_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    invoice_id: Mapped[str] = mapped_column(String(20), ForeignKey("invoices.id"), nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    line_total: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    discount_pct: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False, default=0)
    vat_exempt: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    invoice: Mapped["Invoice"] = relationship(back_populates="items")


class PaymentDetail(Base):
    __tablename__ = "payment_details"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    invoice_id: Mapped[str] = mapped_column(String(20), ForeignKey("invoices.id"), unique=True, nullable=False)
    payment_method: Mapped[str] = mapped_column(String(30), nullable=False)
    payment_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    mpesa_receipt_number: Mapped[str | None] = mapped_column(String(50), nullable=True)
    transaction_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    invoice: Mapped["Invoice"] = relationship(back_populates="payment_detail")


class InvoiceCharge(Base):
    __tablename__ = "invoice_charges"
    __table_args__ = (Index("ix_invoice_charges_invoice_id", "invoice_id"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    invoice_id: Mapped[str] = mapped_column(String(20), ForeignKey("invoices.id"), nullable=False)
    description: Mapped[str] = mapped_column(String(200), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    vat_exempt: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    invoice: Mapped["Invoice"] = relationship(back_populates="charges")


class SequenceCounter(Base):
    __tablename__ = "sequence_counters"

    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("organizations.id"), primary_key=True)
    entity_type: Mapped[str] = mapped_column(String(20), primary_key=True)  # quotation | invoice
    year: Mapped[int] = mapped_column(Integer, primary_key=True)
    last_sequence_number: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
