import uuid
from datetime import datetime, timezone
from decimal import Decimal

from pydantic import BaseModel, computed_field

from app.schemas.client import ClientOut


class InvoiceItemOut(BaseModel):
    id: uuid.UUID
    description: str
    quantity: Decimal
    unit_price: Decimal
    line_total: Decimal
    vat_exempt: bool
    sort_order: int

    model_config = {"from_attributes": True}


class PaymentDetailOut(BaseModel):
    id: uuid.UUID
    payment_method: str
    payment_date: datetime
    mpesa_receipt_number: str | None
    transaction_id: str | None
    notes: str | None

    model_config = {"from_attributes": True}


class MarkPaidRequest(BaseModel):
    payment_method: str  # mpesa | bank | cash
    payment_date: datetime
    mpesa_receipt_number: str | None = None
    transaction_id: str | None = None
    notes: str | None = None


class MpesaPayRequest(BaseModel):
    phone_number: str  # 254XXXXXXXXX


class EtimsSubmitRequest(BaseModel):
    pass  # no body needed; all data comes from the invoice + org


class InvoiceOut(BaseModel):
    id: str
    quotation_id: str | None
    client_id: uuid.UUID
    client: ClientOut
    payment_status: str
    payment_method: str | None
    subtotal: Decimal
    vat_amount: Decimal
    grand_total: Decimal
    amount_paid: Decimal
    due_date: datetime | None
    mpesa_checkout_request_id: str | None
    reminders_sent: int
    last_reminded_at: datetime | None
    items: list[InvoiceItemOut]
    payment_detail: PaymentDetailOut | None
    etims_cu_invoice_no: str | None
    etims_rcpt_sign: str | None
    etims_int_data: str | None
    etims_submitted_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

    @computed_field
    @property
    def balance_due(self) -> Decimal:
        return self.grand_total - self.amount_paid

    @computed_field
    @property
    def is_overdue(self) -> bool:
        if self.payment_status not in ("unpaid", "partial") or self.due_date is None:
            return False
        return self.due_date < datetime.now(timezone.utc)


class InvoiceListOut(BaseModel):
    id: str
    client: ClientOut
    payment_status: str
    grand_total: Decimal
    due_date: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}

    @computed_field
    @property
    def is_overdue(self) -> bool:
        if self.payment_status != "unpaid" or self.due_date is None:
            return False
        return self.due_date < datetime.now(timezone.utc)
