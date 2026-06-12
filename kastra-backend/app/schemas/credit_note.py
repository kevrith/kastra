import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, field_validator


class CreditNoteItemCreate(BaseModel):
    description: str
    quantity: Decimal
    unit_price: Decimal
    vat_exempt: bool = False

    @field_validator("quantity", "unit_price")
    @classmethod
    def non_negative(cls, v: Decimal) -> Decimal:
        if v < 0:
            raise ValueError("must be non-negative")
        return v


class CreditNoteCreate(BaseModel):
    invoice_id: str
    reason: str
    items: list[CreditNoteItemCreate]

    @field_validator("reason")
    @classmethod
    def reason_required(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("reason is required")
        return v.strip()

    @field_validator("items")
    @classmethod
    def items_required(cls, v: list) -> list:
        if not v:
            raise ValueError("at least one item is required")
        return v


class CreditNoteItemOut(BaseModel):
    id: uuid.UUID
    description: str
    quantity: Decimal
    unit_price: Decimal
    line_total: Decimal
    vat_exempt: bool
    sort_order: int

    model_config = {"from_attributes": True}


class CreditNoteOut(BaseModel):
    id: str
    invoice_id: str
    client_id: uuid.UUID
    reason: str
    status: str
    currency: str
    exchange_rate: Decimal
    subtotal: Decimal
    vat_amount: Decimal
    grand_total: Decimal
    etims_cu_invoice_no: str | None
    etims_submitted_at: datetime | None
    created_at: datetime
    items: list[CreditNoteItemOut]

    model_config = {"from_attributes": True}


class CreditNoteListOut(BaseModel):
    id: str
    invoice_id: str
    client_id: uuid.UUID
    reason: str
    status: str
    currency: str
    grand_total: Decimal
    etims_cu_invoice_no: str | None
    created_at: datetime

    model_config = {"from_attributes": True}
