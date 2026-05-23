from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr


class InviteUserRequest(BaseModel):
    email: EmailStr
    role: str  # admin | manager | field_agent | viewer
    display_name: str


class TeamMemberOut(BaseModel):
    id: UUID
    email: str
    display_name: str
    role: str
    is_active: bool
    last_login_at: datetime | None
    invited_at: datetime | None
    invited_by: UUID | None
    created_at: datetime
    invite_link: str | None = None

    class Config:
        from_attributes = True


class AcceptInviteRequest(BaseModel):
    token: str
    password: str


class UpdateTeamMemberRequest(BaseModel):
    role: str | None = None
    is_active: bool | None = None
