import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class CreditNote(Base):
    __tablename__ = "credit_notes"
    __table_args__ = (
        Index("ix_credit_notes_organization_id", "organization_id"),
        Index("ix_credit_notes_invoice_id", "invoice_id"),
        Index("ix_credit_notes_client_id", "client_id"),
    )

    id: Mapped[str] = mapped_column(String(30), primary_key=True)  # PREFIX-CN-YYYY-XXX
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    invoice_id: Mapped[str] = mapped_column(String(20), ForeignKey("invoices.id"), nullable=False)
    client_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("clients.id"), nullable=False)
    reason: Mapped[str] = mapped_column(String(500), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="issued")  # issued | voided
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="KES")
    exchange_rate: Mapped[Decimal] = mapped_column(Numeric(12, 6), nullable=False, default=1)
    subtotal: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False, default=0)
    vat_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False, default=0)
    grand_total: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False, default=0)
    # eTIMS / KRA (credit note = refund receipt referencing the original invoice)
    etims_cu_invoice_no: Mapped[str | None] = mapped_column(String(50), nullable=True)
    etims_rcpt_sign: Mapped[str | None] = mapped_column(Text, nullable=True)
    etims_int_data: Mapped[str | None] = mapped_column(Text, nullable=True)
    etims_submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    invoice: Mapped["Invoice"] = relationship()  # noqa: F821
    client: Mapped["Client"] = relationship()  # noqa: F821
    items: Mapped[list["CreditNoteItem"]] = relationship(
        back_populates="credit_note", cascade="all, delete-orphan", order_by="CreditNoteItem.sort_order"
    )


class CreditNoteItem(Base):
    __tablename__ = "credit_note_items"
    __table_args__ = (
        Index("ix_credit_note_items_credit_note_id", "credit_note_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    credit_note_id: Mapped[str] = mapped_column(String(30), ForeignKey("credit_notes.id"), nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    line_total: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    vat_exempt: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    credit_note: Mapped["CreditNote"] = relationship(back_populates="items")
