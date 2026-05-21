import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class AdminAuditLog(Base):
    __tablename__ = "admin_audit_log"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    # change_plan | suspend | unsuspend | extend_trial | record_payment | grant_access
    target_org_id: Mapped[str] = mapped_column(String(36), nullable=False)
    target_org_name: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    details: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON string
    performed_by: Mapped[str] = mapped_column(String(50), nullable=False, default="superadmin")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
