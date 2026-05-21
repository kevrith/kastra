import uuid
from datetime import datetime, timezone
from decimal import Decimal

from pydantic import BaseModel, computed_field

from app.schemas.client import ClientOut


class InvoiceChargeCreate(BaseModel):
    description: str
    amount: Decimal
    vat_exempt: bool = False
    sort_order: int = 0


class InvoiceChargeOut(BaseModel):
    id: uuid.UUID
    description: str
    amount: Decimal
    vat_exempt: bool
    sort_order: int

    model_config = {"from_attributes": True}


class InvoiceItemCreate(BaseModel):
    description: str
    quantity: Decimal
    unit_price: Decimal
    discount_pct: Decimal = Decimal("0")
    vat_exempt: bool = False
    sort_order: int = 0


class InvoiceCreate(BaseModel):
    client_id: uuid.UUID
    lpo_number: str | None = None
    due_date: datetime | None = None
    notes: str | None = None
    discount_pct: Decimal = Decimal("0")
    wht_pct: Decimal = Decimal("0")
    deposit_amount: Decimal = Decimal("0")
    items: list[InvoiceItemCreate]
    charges: list[InvoiceChargeCreate] = []


class InvoiceItemOut(BaseModel):
    id: uuid.UUID
    description: str
    quantity: Decimal
    unit_price: Decimal
    line_total: Decimal
    discount_pct: Decimal
    vat_exempt: bool
    sort_order: int

    model_config = {"from_attributes": True}

    @computed_field
    @property
    def discount_amount(self) -> Decimal:
        return (self.quantity * self.unit_price * self.discount_pct / 100).quantize(Decimal("0.01"))


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
    lpo_number: str | None
    client_id: uuid.UUID
    client: ClientOut
    payment_status: str
    payment_method: str | None
    subtotal: Decimal
    total_discount: Decimal
    charges_total: Decimal
    discount_pct: Decimal
    wht_pct: Decimal
    wht_amount: Decimal
    deposit_amount: Decimal
    vat_amount: Decimal
    grand_total: Decimal
    amount_paid: Decimal
    due_date: datetime | None
    mpesa_checkout_request_id: str | None
    reminders_sent: int
    last_reminded_at: datetime | None
    items: list[InvoiceItemOut]
    charges: list[InvoiceChargeOut]
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
    def amount_payable(self) -> Decimal:
        return self.grand_total - self.wht_amount - self.deposit_amount

    @computed_field
    @property
    def balance_due(self) -> Decimal:
        return self.amount_payable - self.amount_paid

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
    lpo_number: str | None
    quotation_id: str | None
    created_at: datetime

    model_config = {"from_attributes": True}

    @computed_field
    @property
    def is_overdue(self) -> bool:
        if self.payment_status != "unpaid" or self.due_date is None:
            return False
        return self.due_date < datetime.now(timezone.utc)
