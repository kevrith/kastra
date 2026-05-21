import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Client(Base):
    __tablename__ = "clients"
    __table_args__ = (
        Index("ix_clients_organization_id", "organization_id"),
        Index("ix_clients_name", "name"),
        Index("ix_clients_status", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    portal_token: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), unique=True, nullable=False, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)  # 254XXXXXXXXX format
    address: Mapped[str | None] = mapped_column(String(500), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")  # active | inactive
    portal_pin_hash: Mapped[str | None] = mapped_column(String(60), nullable=True)  # bcrypt hash; None = no PIN required
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    organization: Mapped["Organization"] = relationship(back_populates="clients")  # noqa: F821
    quotations: Mapped[list["Quotation"]] = relationship(back_populates="client")  # noqa: F821
    invoices: Mapped[list["Invoice"]] = relationship(back_populates="client")  # noqa: F821
    recurring_invoices: Mapped[list["RecurringInvoice"]] = relationship(back_populates="client")  # noqa: F821
