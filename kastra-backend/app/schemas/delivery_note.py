import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, field_validator


class DeliveryNoteItemCreate(BaseModel):
    description: str
    quantity: Decimal
    unit: str | None = None

    @field_validator("quantity")
    @classmethod
    def positive(cls, v: Decimal) -> Decimal:
        if v <= 0:
            raise ValueError("quantity must be positive")
        return v


class DeliveryNoteCreate(BaseModel):
    client_id: uuid.UUID | None = None  # derived from invoice/quotation when omitted
    invoice_id: str | None = None
    quotation_id: str | None = None
    lpo_number: str | None = None
    delivery_date: datetime | None = None
    vehicle_reg: str | None = None
    driver_name: str | None = None
    notes: str | None = None
    items: list[DeliveryNoteItemCreate] | None = None  # defaults to source document items


class DeliveryNoteUpdate(BaseModel):
    delivery_date: datetime | None = None
    vehicle_reg: str | None = None
    driver_name: str | None = None
    received_by: str | None = None
    notes: str | None = None
    status: str | None = None  # issued | delivered


class DeliveryNoteItemOut(BaseModel):
    id: uuid.UUID
    description: str
    quantity: Decimal
    unit: str | None
    sort_order: int

    model_config = {"from_attributes": True}


class DeliveryNoteOut(BaseModel):
    id: str
    invoice_id: str | None
    quotation_id: str | None
    client_id: uuid.UUID
    lpo_number: str | None
    delivery_date: datetime | None
    vehicle_reg: str | None
    driver_name: str | None
    received_by: str | None
    notes: str | None
    status: str
    created_at: datetime
    items: list[DeliveryNoteItemOut]

    model_config = {"from_attributes": True}
