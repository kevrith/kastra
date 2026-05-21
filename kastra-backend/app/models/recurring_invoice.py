import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class RecurringInvoice(Base):
    __tablename__ = "recurring_invoices"
    __table_args__ = (
        Index("ix_recurring_invoices_organization_id", "organization_id"),
        Index("ix_recurring_invoices_client_id", "client_id"),
        Index("ix_recurring_invoices_is_active", "is_active"),
        Index("ix_recurring_invoices_next_run_at", "next_run_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    client_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("clients.id"), nullable=False)
    frequency: Mapped[str] = mapped_column(String(20), nullable=False)  # weekly|monthly|quarterly|yearly
    items: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)  # [{description, quantity, unit_price}]
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    next_run_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    organization: Mapped["Organization"] = relationship(back_populates="recurring_invoices")  # noqa: F821
    client: Mapped["Client"] = relationship(back_populates="recurring_invoices")  # noqa: F821
