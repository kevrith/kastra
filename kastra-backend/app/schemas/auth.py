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
    referral_code: str | None = None  # affiliate referral code


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class LoginResponse(BaseModel):
    """Login either signs you in or hands back a 2FA challenge.

    `access_token` stays populated for accounts without 2FA, so existing clients
    are unaffected; when `mfa_required` is set the caller must exchange
    `mfa_token` plus a code at /api/auth/2fa/verify-login.
    """
    access_token: str | None = None
    token_type: str = "bearer"
    mfa_required: bool = False
    mfa_token: str | None = None


# ── Two-factor authentication ────────────────────────────────────────────────

class TotpSetupResponse(BaseModel):
    secret: str                 # shown for manual entry when a QR cannot be scanned
    otpauth_uri: str
    qr_data_uri: str


class TotpEnableRequest(BaseModel):
    code: str


class TotpEnableResponse(BaseModel):
    backup_codes: list[str]     # returned exactly once, at enable time


class TotpDisableRequest(BaseModel):
    password: str
    code: str | None = None


class TotpLoginRequest(BaseModel):
    mfa_token: str
    code: str


class TotpStatusResponse(BaseModel):
    enabled: bool
    confirmed_at: datetime | None = None
    backup_codes_remaining: int = 0


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


class ResendVerificationRequest(BaseModel):
    email: EmailStr
