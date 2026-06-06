import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

from pydantic import BaseModel, computed_field, field_validator

from app.schemas.client import ClientOut


class InvoiceExpenseOut(BaseModel):
    id: uuid.UUID
    category: str
    description: str
    vendor: str | None
    amount: float
    date: date
    invoice_id: str | None = None

    model_config = {"from_attributes": True}


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
    cost_price: Decimal = Decimal("0")
    discount_pct: Decimal = Decimal("0")
    vat_exempt: bool = False
    sort_order: int = 0


class InvoiceCreate(BaseModel):
    client_id: uuid.UUID
    invoice_date: datetime | None = None
    lpo_number: str | None = None
    due_date: datetime | None = None
    notes: str | None = None
    discount_pct: Decimal = Decimal("0")
    wht_pct: Decimal = Decimal("0")
    deposit_amount: Decimal = Decimal("0")
    currency: str = "KES"
    exchange_rate: Decimal = Decimal("1")
    items: list[InvoiceItemCreate]
    charges: list[InvoiceChargeCreate] = []

    @field_validator("currency")
    @classmethod
    def valid_currency(cls, v: str) -> str:
        v = (v or "KES").upper().strip()
        if len(v) != 3 or not v.isalpha():
            raise ValueError("currency must be a 3-letter ISO code, e.g. KES, USD, EUR")
        return v

    @field_validator("exchange_rate")
    @classmethod
    def valid_exchange_rate(cls, v: Decimal) -> Decimal:
        if v <= 0:
            raise ValueError("exchange_rate must be greater than zero")
        return v


class InvoiceItemOut(BaseModel):
    id: uuid.UUID
    description: str
    quantity: Decimal
    unit_price: Decimal
    cost_price: Decimal = Decimal("0")
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
    currency: str
    exchange_rate: Decimal
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
    invoice_date: datetime | None
    due_date: datetime | None
    mpesa_checkout_request_id: str | None
    reminders_sent: int
    last_reminded_at: datetime | None
    items: list[InvoiceItemOut]
    charges: list[InvoiceChargeOut]
    expenses: list[InvoiceExpenseOut] = []
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
    def kes_equivalent(self) -> Decimal:
        return (self.grand_total * self.exchange_rate).quantize(Decimal("0.01"))

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

    @computed_field
    @property
    def total_cogs(self) -> Decimal:
        """Cost of goods sold: sum of cost_price × quantity for all line items."""
        return sum(
            (item.cost_price * item.quantity).quantize(Decimal("0.01"))
            for item in self.items
        )

    @computed_field
    @property
    def total_job_expenses(self) -> Decimal:
        """Sum of all expenses attached to this invoice."""
        return Decimal(str(sum(e.amount for e in self.expenses))).quantize(Decimal("0.01"))

    @computed_field
    @property
    def gross_profit(self) -> Decimal:
        """Revenue minus COGS and job expenses, expressed in KES.

        Job expenses are always tracked in KES (real cash spent locally), so revenue
        and COGS are converted to their KES equivalent before netting them out —
        otherwise foreign-currency invoices would mix units and produce a nonsense figure.
        """
        revenue_kes = self.grand_total * self.exchange_rate
        cogs_kes = self.total_cogs * self.exchange_rate
        return (revenue_kes - cogs_kes - self.total_job_expenses).quantize(Decimal("0.01"))

    @computed_field
    @property
    def is_profitable(self) -> bool:
        return self.gross_profit >= Decimal("0")


class InvoiceListOut(BaseModel):
    id: str
    client: ClientOut
    payment_status: str
    currency: str
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
