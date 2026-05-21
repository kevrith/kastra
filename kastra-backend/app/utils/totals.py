from decimal import Decimal

VAT_RATE = Decimal("0.16")
DEFAULT_WHT_PCT = Decimal("1.5")


def calculate_totals(items, charges=None, discount_pct=Decimal("0"), wht_pct=Decimal("0")):
    """
    Returns a dict with all financial fields for an invoice or quotation.

    Calculation chain:
      items_gross = sum(qty × unit_price)
      line_discounts = sum per item of (gross × item.discount_pct%)
      overall_discount = (items_gross - line_discounts) × discount_pct%
      total_discount = line_discounts + overall_discount
      items_net = items_gross - total_discount
      charges_total = sum of extra charge amounts
      vat = (taxable items net + taxable charges) × 16%
      grand_total = items_net + charges_total + vat
      wht_amount = items_net × wht_pct%   ← deducted by client before paying
    """
    discount_pct = Decimal(str(discount_pct))
    wht_pct = Decimal(str(wht_pct))
    charges = charges or []

    # Gross subtotal (qty × unit_price, no discounts)
    subtotal = sum(
        (Decimal(str(i.quantity)) * Decimal(str(i.unit_price)) for i in items),
        Decimal("0"),
    )

    # Per-line discounts
    line_discounts = sum(
        (Decimal(str(i.quantity)) * Decimal(str(i.unit_price)) * Decimal(str(getattr(i, "discount_pct", 0))) / 100
        for i in items),
        Decimal("0"),
    ).quantize(Decimal("0.01"))

    # Net items after line discounts
    items_after_line = subtotal - line_discounts

    # Overall document discount (applied to net-of-line-discounts total)
    overall_discount = (items_after_line * discount_pct / 100).quantize(Decimal("0.01"))

    total_discount = (line_discounts + overall_discount).quantize(Decimal("0.01"))
    items_net = subtotal - total_discount

    # Other charges
    charges_total = sum((Decimal(str(c.amount)) for c in charges), Decimal("0")).quantize(Decimal("0.01"))

    # VAT — on taxable items (after all discounts) + taxable charges
    taxable_items_gross = sum(
        (Decimal(str(i.quantity)) * Decimal(str(i.unit_price))
        for i in items if not getattr(i, "vat_exempt", False)),
        Decimal("0"),
    )
    taxable_line_discounts = sum(
        (Decimal(str(i.quantity)) * Decimal(str(i.unit_price)) * Decimal(str(getattr(i, "discount_pct", 0))) / 100
        for i in items if not getattr(i, "vat_exempt", False)),
        Decimal("0"),
    ).quantize(Decimal("0.01"))
    taxable_items_net = taxable_items_gross - taxable_line_discounts
    taxable_items_discounted = (taxable_items_net * (1 - discount_pct / 100)).quantize(Decimal("0.01"))
    taxable_charges = sum(
        (Decimal(str(c.amount)) for c in charges if not getattr(c, "vat_exempt", False)),
        Decimal("0"),
    ).quantize(Decimal("0.01"))

    vat_amount = ((taxable_items_discounted + taxable_charges) * VAT_RATE).quantize(Decimal("0.01"))

    grand_total = (items_net + charges_total + vat_amount).quantize(Decimal("0.01"))

    # WHT — deducted by client from net items amount (before VAT), paid to KRA on your behalf
    wht_amount = (items_net * wht_pct / 100).quantize(Decimal("0.01"))

    return {
        "subtotal": subtotal,
        "total_discount": total_discount,
        "charges_total": charges_total,
        "vat_amount": vat_amount,
        "grand_total": grand_total,
        "wht_amount": wht_amount,
    }
