from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr


class InviteUserRequest(BaseModel):
    email: EmailStr
    role: str
    display_name: str


class PermissionsOut(BaseModel):
    can_view_invoices: bool = False
    can_create_invoices: bool = False
    can_edit_invoices: bool = False
    can_delete_invoices: bool = False
    can_view_quotations: bool = False
    can_create_quotations: bool = False
    can_edit_quotations: bool = False
    can_delete_quotations: bool = False
    can_view_clients: bool = False
    can_create_clients: bool = False
    can_edit_clients: bool = False
    can_delete_clients: bool = False
    can_view_reports: bool = False
    can_view_expenses: bool = False
    can_create_expenses: bool = False
    can_view_projects: bool = False
    can_manage_projects: bool = False

    model_config = {"from_attributes": True}


class UpdatePermissionsRequest(BaseModel):
    can_view_invoices: bool = False
    can_create_invoices: bool = False
    can_edit_invoices: bool = False
    can_delete_invoices: bool = False
    can_view_quotations: bool = False
    can_create_quotations: bool = False
    can_edit_quotations: bool = False
    can_delete_quotations: bool = False
    can_view_clients: bool = False
    can_create_clients: bool = False
    can_edit_clients: bool = False
    can_delete_clients: bool = False
    can_view_reports: bool = False
    can_view_expenses: bool = False
    can_create_expenses: bool = False
    can_view_projects: bool = False
    can_manage_projects: bool = False


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
    invite_token: str | None = None
    invite_link: str | None = None

    class Config:
        from_attributes = True


class AcceptInviteRequest(BaseModel):
    token: str
    password: str


class UpdateTeamMemberRequest(BaseModel):
    role: str | None = None
    is_active: bool | None = None
