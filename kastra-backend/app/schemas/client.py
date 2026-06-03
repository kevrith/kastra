import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, field_validator


class ClientCreate(BaseModel):
    name: str
    email: str | None = None
    phone: str | None = None
    address: str | None = None
    sms_consent: bool = False

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str | None) -> str | None:
        if v is None:
            return v
        digits = v.replace("+", "").replace(" ", "")
        if not digits.isdigit():
            raise ValueError("Phone must contain only digits")
        if digits.startswith("0") and len(digits) == 10:
            digits = "254" + digits[1:]
        if not digits.startswith("254") or len(digits) != 12:
            raise ValueError("Phone must be in 254XXXXXXXXX format (12 digits)")
        return digits


class ClientUpdate(BaseModel):
    name: str | None = None
    email: str | None = None
    phone: str | None = None
    address: str | None = None
    status: str | None = None
    sms_consent: bool | None = None

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str | None) -> str | None:
        if v is None:
            return v
        digits = v.replace("+", "").replace(" ", "")
        if not digits.isdigit():
            raise ValueError("Phone must contain only digits")
        if digits.startswith("0") and len(digits) == 10:
            digits = "254" + digits[1:]
        if not digits.startswith("254") or len(digits) != 12:
            raise ValueError("Phone must be in 254XXXXXXXXX format (12 digits)")
        return digits


class ClientOut(BaseModel):
    id: uuid.UUID
    portal_token: uuid.UUID
    name: str
    email: str | None
    phone: str | None
    address: str | None
    status: str
    sms_consent: bool = False
    pin_enabled: bool = False
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

    @classmethod
    def model_validate(cls, obj, *args, **kwargs):
        # Compute pin_enabled from portal_pin_hash without exposing the hash
        instance = super().model_validate(obj, *args, **kwargs)
        if hasattr(obj, "portal_pin_hash"):
            instance.pin_enabled = obj.portal_pin_hash is not None
        return instance


class ClientStats(BaseModel):
    total_billed: Decimal
    invoice_count: int
    paid_count: int
    unpaid_count: int
