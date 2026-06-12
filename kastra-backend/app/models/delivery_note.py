import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Index, Integer, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class DeliveryNote(Base):
    __tablename__ = "delivery_notes"
    __table_args__ = (
        Index("ix_delivery_notes_organization_id", "organization_id"),
        Index("ix_delivery_notes_invoice_id", "invoice_id"),
        Index("ix_delivery_notes_client_id", "client_id"),
    )

    id: Mapped[str] = mapped_column(String(30), primary_key=True)  # PREFIX-DN-YYYY-XXX
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    invoice_id: Mapped[str | None] = mapped_column(String(20), ForeignKey("invoices.id"), nullable=True)
    quotation_id: Mapped[str | None] = mapped_column(String(20), ForeignKey("quotations.id"), nullable=True)
    client_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("clients.id"), nullable=False)
    lpo_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    delivery_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    vehicle_reg: Mapped[str | None] = mapped_column(String(30), nullable=True)
    driver_name: Mapped[str | None] = mapped_column(String(150), nullable=True)
    received_by: Mapped[str | None] = mapped_column(String(150), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="issued")  # issued | delivered
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    invoice: Mapped["Invoice | None"] = relationship()  # noqa: F821
    client: Mapped["Client"] = relationship()  # noqa: F821
    items: Mapped[list["DeliveryNoteItem"]] = relationship(
        back_populates="delivery_note", cascade="all, delete-orphan", order_by="DeliveryNoteItem.sort_order"
    )


class DeliveryNoteItem(Base):
    __tablename__ = "delivery_note_items"
    __table_args__ = (
        Index("ix_delivery_note_items_delivery_note_id", "delivery_note_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    delivery_note_id: Mapped[str] = mapped_column(String(30), ForeignKey("delivery_notes.id"), nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    unit: Mapped[str | None] = mapped_column(String(30), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    delivery_note: Mapped["DeliveryNote"] = relationship(back_populates="items")
