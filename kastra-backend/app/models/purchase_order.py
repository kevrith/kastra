import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, ForeignKey, Index, Integer, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class PurchaseOrder(Base):
    """A formal order placed with a supplier (the buy-side of the P2P cycle).

    Status machine:
      draft -> sent -> (supplier_confirmed | supplier_revised) -> [rejected ↺ sent]
            -> accepted -> receiving -> received -> billed -> paid
      (cancelled at any point)
    """
    __tablename__ = "purchase_orders"
    __table_args__ = (
        Index("ix_purchase_orders_organization_id", "organization_id"),
        Index("ix_purchase_orders_supplier_id", "supplier_id"),
        Index("ix_purchase_orders_status", "status"),
        Index("ix_purchase_orders_created_at", "created_at"),
        UniqueConstraint("portal_token", name="uq_purchase_order_token"),
    )

    id: Mapped[str] = mapped_column(String(20), primary_key=True)  # PREFIX-PO-YYYY-XXX
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    supplier_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("suppliers.id"), nullable=False)
    created_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    source_request_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("supplier_requests.id", ondelete="SET NULL"), nullable=True
    )

    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")
    portal_token: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), unique=True, nullable=False, default=uuid.uuid4)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="KES")

    expected_delivery: Mapped[date | None] = mapped_column(Date, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)  # buyer instructions to supplier
    supplier_notes: Mapped[str | None] = mapped_column(Text, nullable=True)  # supplier's note on response

    # Ordered amounts (what the buyer asked for)
    subtotal: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False, default=0)
    tax_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False, default=0)
    total: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False, default=0)
    # Confirmed amount (what the supplier came back with); null until they respond
    confirmed_total: Mapped[Decimal | None] = mapped_column(Numeric(15, 2), nullable=True)

    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    received_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    supplier: Mapped["Supplier"] = relationship()  # noqa: F821
    items: Mapped[list["PurchaseOrderItem"]] = relationship(
        back_populates="purchase_order", cascade="all, delete-orphan", order_by="PurchaseOrderItem.sort_order"
    )
    notes_thread: Mapped[list["PurchaseOrderNote"]] = relationship(
        back_populates="purchase_order", cascade="all, delete-orphan", order_by="PurchaseOrderNote.created_at"
    )


class PurchaseOrderItem(Base):
    __tablename__ = "purchase_order_items"
    __table_args__ = (
        Index("ix_purchase_order_items_purchase_order_id", "purchase_order_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    purchase_order_id: Mapped[str] = mapped_column(String(20), ForeignKey("purchase_orders.id", ondelete="CASCADE"), nullable=False)
    product_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("products.id", ondelete="SET NULL"), nullable=True)
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    unit: Mapped[str | None] = mapped_column(String(50), nullable=True)

    ordered_qty: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    ordered_unit_price: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False, default=0)
    confirmed_qty: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    confirmed_unit_price: Mapped[Decimal | None] = mapped_column(Numeric(15, 2), nullable=True)
    received_qty: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    line_total: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False, default=0)  # ordered line total
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    purchase_order: Mapped["PurchaseOrder"] = relationship(back_populates="items")
    product: Mapped["Product"] = relationship()  # noqa: F821


class PurchaseOrderNote(Base):
    """Negotiation thread: buyer rejection reasons and supplier replies."""
    __tablename__ = "purchase_order_notes"
    __table_args__ = (
        Index("ix_purchase_order_notes_purchase_order_id", "purchase_order_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    purchase_order_id: Mapped[str] = mapped_column(String(20), ForeignKey("purchase_orders.id", ondelete="CASCADE"), nullable=False)
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)  # null = supplier via portal
    author_type: Mapped[str] = mapped_column(String(20), nullable=False, default="buyer")  # buyer | supplier
    body: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    purchase_order: Mapped["PurchaseOrder"] = relationship(back_populates="notes_thread")
    author: Mapped["User"] = relationship(foreign_keys=[created_by])  # noqa: F821


class GoodsReceipt(Base):
    """A Goods Receipt Note (GRN): what actually arrived against a PO. Supports partials."""
    __tablename__ = "goods_receipts"
    __table_args__ = (
        Index("ix_goods_receipts_organization_id", "organization_id"),
        Index("ix_goods_receipts_purchase_order_id", "purchase_order_id"),
    )

    id: Mapped[str] = mapped_column(String(20), primary_key=True)  # PREFIX-GRN-YYYY-XXX
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    purchase_order_id: Mapped[str] = mapped_column(String(20), ForeignKey("purchase_orders.id", ondelete="CASCADE"), nullable=False)
    received_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    received_date: Mapped[date] = mapped_column(Date, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    items: Mapped[list["GoodsReceiptItem"]] = relationship(
        back_populates="goods_receipt", cascade="all, delete-orphan", order_by="GoodsReceiptItem.sort_order"
    )


class GoodsReceiptItem(Base):
    __tablename__ = "goods_receipt_items"
    __table_args__ = (
        Index("ix_goods_receipt_items_goods_receipt_id", "goods_receipt_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    goods_receipt_id: Mapped[str] = mapped_column(String(20), ForeignKey("goods_receipts.id", ondelete="CASCADE"), nullable=False)
    purchase_order_item_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("purchase_order_items.id", ondelete="SET NULL"), nullable=True
    )
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False, default=0)  # cost at receipt
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    goods_receipt: Mapped["GoodsReceipt"] = relationship(back_populates="items")


class SupplierBill(Base):
    """Accounts Payable: what the business owes a supplier. Supports 3-way match against PO + GRN."""
    __tablename__ = "supplier_bills"
    __table_args__ = (
        Index("ix_supplier_bills_organization_id", "organization_id"),
        Index("ix_supplier_bills_supplier_id", "supplier_id"),
        Index("ix_supplier_bills_status", "status"),
        Index("ix_supplier_bills_due_date", "due_date"),
    )

    id: Mapped[str] = mapped_column(String(20), primary_key=True)  # PREFIX-BILL-YYYY-XXX
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    supplier_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("suppliers.id"), nullable=False)
    purchase_order_id: Mapped[str | None] = mapped_column(String(20), ForeignKey("purchase_orders.id", ondelete="SET NULL"), nullable=True)
    goods_receipt_id: Mapped[str | None] = mapped_column(String(20), ForeignKey("goods_receipts.id", ondelete="SET NULL"), nullable=True)

    supplier_ref: Mapped[str | None] = mapped_column(String(100), nullable=True)  # supplier's own invoice number
    bill_date: Mapped[date] = mapped_column(Date, nullable=False)
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    subtotal: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False, default=0)
    tax_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False, default=0)
    total: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False, default=0)
    amount_paid: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False, default=0)

    status: Mapped[str] = mapped_column(String(20), nullable=False, default="unpaid")  # unpaid | partial | paid
    match_status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")  # matched | mismatch | pending
    match_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    supplier: Mapped["Supplier"] = relationship()  # noqa: F821


class SupplierPriceHistory(Base):
    """Records every confirmed/received price per supplier+item, to flag price changes over time."""
    __tablename__ = "supplier_price_history"
    __table_args__ = (
        Index("ix_supplier_price_history_org_supplier", "organization_id", "supplier_id"),
        Index("ix_supplier_price_history_lookup", "supplier_id", "description"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    supplier_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("suppliers.id", ondelete="CASCADE"), nullable=False)
    product_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("products.id", ondelete="SET NULL"), nullable=True)
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    source_po_id: Mapped[str | None] = mapped_column(String(20), nullable=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
