import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Quotation(Base):
    __tablename__ = "quotations"
    __table_args__ = (
        Index("ix_quotations_organization_id", "organization_id"),
        Index("ix_quotations_client_id", "client_id"),
        Index("ix_quotations_status", "status"),
        Index("ix_quotations_created_at", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(20), primary_key=True)  # QT-YYYY-XXX
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    client_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("clients.id"), nullable=False)
    created_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")  # draft|pending|accepted|declined
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="KES")
    exchange_rate: Mapped[Decimal] = mapped_column(Numeric(12, 6), nullable=False, default=1)
    subtotal: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False, default=0)
    vat_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False, default=0)
    grand_total: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False, default=0)
    project_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    project_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    decline_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    discount_pct: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False, default=0)
    total_discount: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False, default=0)
    charges_total: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False, default=0)
    wht_pct: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False, default=0)
    wht_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False, default=0)
    converted_to_invoice: Mapped[bool] = mapped_column(Boolean, default=False)
    invoice_id: Mapped[str | None] = mapped_column(String(20), ForeignKey("invoices.id"), nullable=True)
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    organization: Mapped["Organization"] = relationship(back_populates="quotations")  # noqa: F821
    client: Mapped["Client"] = relationship(back_populates="quotations")  # noqa: F821
    created_by_user: Mapped["User"] = relationship(back_populates="quotations")  # noqa: F821
    items: Mapped[list["QuotationItem"]] = relationship(
        back_populates="quotation", cascade="all, delete-orphan", order_by="QuotationItem.sort_order"
    )
    charges: Mapped[list["QuotationCharge"]] = relationship(
        back_populates="quotation", cascade="all, delete-orphan", order_by="QuotationCharge.sort_order"
    )


class QuotationItem(Base):
    __tablename__ = "quotation_items"
    __table_args__ = (
        Index("ix_quotation_items_quotation_id", "quotation_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    quotation_id: Mapped[str] = mapped_column(String(20), ForeignKey("quotations.id"), nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    line_total: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    discount_pct: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False, default=0)
    vat_exempt: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    quotation: Mapped["Quotation"] = relationship(back_populates="items")


class QuotationCharge(Base):
    __tablename__ = "quotation_charges"
    __table_args__ = (Index("ix_quotation_charges_quotation_id", "quotation_id"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    quotation_id: Mapped[str] = mapped_column(String(20), ForeignKey("quotations.id"), nullable=False)
    description: Mapped[str] = mapped_column(String(200), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    vat_exempt: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    quotation: Mapped["Quotation"] = relationship(back_populates="charges")
