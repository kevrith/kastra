import uuid
from datetime import datetime

from pydantic import BaseModel


class OrganizationUpdate(BaseModel):
    name: str | None = None
    email: str | None = None
    phone: str | None = None
    address: str | None = None
    kra_pin: str | None = None
    payment_terms_days: int | None = None
    quotation_validity_days: int | None = None
    authorised_by: str | None = None
    logo_url: str | None = None
    document_template: str | None = None
    etims_enabled: bool | None = None
    etims_branch_id: str | None = None
    etims_device_serial: str | None = None
    etims_auth_token: str | None = None
    # Payment credentials — accepted on update, never returned in full
    paystack_secret_key: str | None = None
    mpesa_consumer_key: str | None = None
    mpesa_consumer_secret: str | None = None
    mpesa_shortcode: str | None = None
    mpesa_passkey: str | None = None
    mpesa_env: str | None = None


class OrganizationOut(BaseModel):
    id: uuid.UUID
    name: str
    email: str | None
    phone: str | None
    address: str | None
    kra_pin: str | None
    payment_terms_days: int
    quotation_validity_days: int
    authorised_by: str | None
    logo_url: str | None
    document_template: str
    etims_enabled: bool
    etims_branch_id: str | None
    etims_device_serial: str | None
    created_at: datetime
    updated_at: datetime
    # Credentials are write-only — expose only whether they're configured
    paystack_configured: bool = False
    mpesa_configured: bool = False
    mpesa_env: str = "sandbox"
    # Subscription
    plan: str = "free"
    plan_status: str = "active"
    is_trial: bool = False
    trial_ends_at: datetime | None = None
    invoices_this_month: int = 0
    quotations_this_month: int = 0
    ocr_scans_this_month: int = 0
    billing_cycle_start: datetime | None = None
    next_billing_date: datetime | None = None

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm_with_flags(cls, org) -> "OrganizationOut":
        data = cls.model_validate(org)
        data.paystack_configured = bool(org.paystack_secret_key)
        data.mpesa_configured = bool(org.mpesa_consumer_key and org.mpesa_shortcode and org.mpesa_passkey)
        data.mpesa_env = org.mpesa_env or "sandbox"
        return data
