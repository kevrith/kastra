import uuid
from datetime import datetime, timezone
from decimal import Decimal

from pydantic import BaseModel, computed_field, field_validator

from app.schemas.client import ClientOut


class QuotationItemCreate(BaseModel):
    description: str
    quantity: Decimal
    unit_price: Decimal
    vat_exempt: bool = False
    sort_order: int = 0

    @field_validator("quantity", "unit_price")
    @classmethod
    def must_be_positive(cls, v: Decimal) -> Decimal:
        if v <= 0:
            raise ValueError("Must be greater than zero")
        return v


class QuotationItemOut(BaseModel):
    id: uuid.UUID
    description: str
    quantity: Decimal
    unit_price: Decimal
    line_total: Decimal
    vat_exempt: bool
    sort_order: int

    model_config = {"from_attributes": True}


class QuotationCreate(BaseModel):
    client_id: uuid.UUID
    items: list[QuotationItemCreate]
    notes: str | None = None
    expires_at: datetime | None = None


class QuotationUpdate(BaseModel):
    client_id: uuid.UUID | None = None
    items: list[QuotationItemCreate] | None = None
    notes: str | None = None
    expires_at: datetime | None = None


class QuotationStatusUpdate(BaseModel):
    status: str

    @field_validator("status")
    @classmethod
    def valid_status(cls, v: str) -> str:
        allowed = {"draft", "pending", "accepted", "declined", "expired"}
        if v not in allowed:
            raise ValueError(f"Status must be one of {allowed}")
        return v


class QuotationOut(BaseModel):
    id: str
    client_id: uuid.UUID
    client: ClientOut
    created_by: uuid.UUID
    status: str
    subtotal: Decimal
    vat_amount: Decimal
    grand_total: Decimal
    notes: str | None
    decline_reason: str | None
    expires_at: datetime | None
    converted_to_invoice: bool
    invoice_id: str | None
    items: list[QuotationItemOut]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

    @computed_field
    @property
    def is_expired(self) -> bool:
        if self.status not in ("draft", "pending") or self.expires_at is None:
            return False
        return self.expires_at < datetime.now(timezone.utc)


class QuotationListOut(BaseModel):
    id: str
    client: ClientOut
    status: str
    grand_total: Decimal
    expires_at: datetime | None
    converted_to_invoice: bool
    created_at: datetime

    model_config = {"from_attributes": True}

    @computed_field
    @property
    def is_expired(self) -> bool:
        if self.status not in ("draft", "pending") or self.expires_at is None:
            return False
        return self.expires_at < datetime.now(timezone.utc)
