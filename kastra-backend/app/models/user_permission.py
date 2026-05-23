import uuid
from sqlalchemy import Boolean, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class UserPermission(Base):
    __tablename__ = "user_permissions"
    __table_args__ = (UniqueConstraint("user_id", name="uq_user_permissions_user_id"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # Invoices
    can_view_invoices: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    can_create_invoices: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    can_edit_invoices: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    can_delete_invoices: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Quotations
    can_view_quotations: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    can_create_quotations: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    can_edit_quotations: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    can_delete_quotations: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Clients
    can_view_clients: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    can_create_clients: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    can_edit_clients: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    can_delete_clients: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Reports & Expenses
    can_view_reports: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    can_view_expenses: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    can_create_expenses: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Projects
    can_view_projects: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    can_manage_projects: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    user: Mapped["User"] = relationship(back_populates="permissions")  # noqa: F821
