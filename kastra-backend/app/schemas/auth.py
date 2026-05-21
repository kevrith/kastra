import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr


class RegisterRequest(BaseModel):
    business_name: str
    email: EmailStr
    password: str
    display_name: str
    consent: bool  # Kenya DPA 2019 — explicit consent required
    plan: str = "free"  # free | starter | business | premium


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class OrganizationBrief(BaseModel):
    id: uuid.UUID
    name: str
    email: str | None
    phone: str | None
    address: str | None
    kra_pin: str | None
    payment_terms_days: int
    plan: str = "free"
    plan_status: str = "active"
    is_trial: bool = False
    trial_ends_at: datetime | None = None
    invoices_this_month: int = 0
    quotations_this_month: int = 0
    ocr_scans_this_month: int = 0

    model_config = {"from_attributes": True}


class UserOut(BaseModel):
    id: uuid.UUID
    email: str
    display_name: str
    role: str
    is_active: bool
    organization: OrganizationBrief

    model_config = {"from_attributes": True}


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str
