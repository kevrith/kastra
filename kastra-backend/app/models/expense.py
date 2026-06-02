import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Index, Numeric, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Expense(Base):
    __tablename__ = "expenses"
    __table_args__ = (
        Index("ix_expenses_organization_id", "organization_id"),
        Index("ix_expenses_date", "date"),
        Index("ix_expenses_category", "category"),
        Index("ix_expenses_project_id", "project_id"),
        Index("ix_expenses_invoice_id", "invoice_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    project_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="SET NULL"), nullable=True)
    invoice_id: Mapped[str | None] = mapped_column(String(20), ForeignKey("invoices.id", ondelete="SET NULL"), nullable=True)
    category: Mapped[str] = mapped_column(String(100), nullable=False)  # rent|salaries|utilities|supplies|materials|labour|lunch|transport|fuel|other
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    vendor: Mapped[str | None] = mapped_column(String(200), nullable=True)
    amount: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    organization: Mapped["Organization"] = relationship(back_populates="expenses")  # noqa: F821
    project: Mapped["Project"] = relationship()  # noqa: F821
