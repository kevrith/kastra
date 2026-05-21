import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    address: Mapped[str | None] = mapped_column(String(500), nullable=True)
    kra_pin: Mapped[str | None] = mapped_column(String(20), nullable=True)
    payment_terms_days: Mapped[int] = mapped_column(Integer, nullable=False, default=30)
    quotation_validity_days: Mapped[int] = mapped_column(Integer, nullable=False, default=30)
    authorised_by: Mapped[str | None] = mapped_column(String(200), nullable=True)
    logo_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    document_template: Mapped[str] = mapped_column(String(20), nullable=False, default="classic")
    # Payment credentials (per-org)
    paystack_secret_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
    mpesa_consumer_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
    mpesa_consumer_secret: Mapped[str | None] = mapped_column(String(255), nullable=True)
    mpesa_shortcode: Mapped[str | None] = mapped_column(String(20), nullable=True)
    mpesa_passkey: Mapped[str | None] = mapped_column(String(255), nullable=True)
    mpesa_env: Mapped[str] = mapped_column(String(20), nullable=False, default="sandbox")

    # eTIMS / KRA
    etims_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    etims_branch_id: Mapped[str | None] = mapped_column(String(10), nullable=True)
    etims_device_serial: Mapped[str | None] = mapped_column(String(50), nullable=True)
    etims_auth_token: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    users: Mapped[list["User"]] = relationship(back_populates="organization")  # noqa: F821
    clients: Mapped[list["Client"]] = relationship(back_populates="organization")  # noqa: F821
    quotations: Mapped[list["Quotation"]] = relationship(back_populates="organization")  # noqa: F821
    invoices: Mapped[list["Invoice"]] = relationship(back_populates="organization")  # noqa: F821
    expenses: Mapped[list["Expense"]] = relationship(back_populates="organization")  # noqa: F821
    products: Mapped[list["Product"]] = relationship(back_populates="organization")  # noqa: F821
    notifications: Mapped[list["Notification"]] = relationship(back_populates="organization")  # noqa: F821
    recurring_invoices: Mapped[list["RecurringInvoice"]] = relationship(back_populates="organization")  # noqa: F821
