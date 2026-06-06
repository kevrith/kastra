"""Kenyan statutory payroll calculations (PAYE, NSSF, SHIF, Affordable Housing Levy).

Rates reflect the post-2024 tax reform regime, where NSSF, SHIF and the
Housing Levy are allowable deductions that reduce taxable income BEFORE PAYE
is computed, and Personal Relief is then subtracted from the resulting tax.
"""
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

TWO_PLACES = Decimal("0.01")

# --- PAYE monthly tax bands (Finance Act 2023) ---
# (band upper bound, rate) — last band has no upper bound (None)
PAYE_BANDS = [
    (Decimal("24000"), Decimal("0.10")),
    (Decimal("32333"), Decimal("0.25")),
    (Decimal("500000"), Decimal("0.30")),
    (Decimal("800000"), Decimal("0.325")),
    (None, Decimal("0.35")),
]

PERSONAL_RELIEF = Decimal("2400.00")

# --- NSSF (NSSF Act 2013, phased implementation) ---
NSSF_LOWER_EARNINGS_LIMIT = Decimal("8000")
NSSF_UPPER_EARNINGS_LIMIT = Decimal("72000")
NSSF_RATE = Decimal("0.06")

# --- SHIF (Social Health Insurance Fund, replaced NHIF Oct 2024) ---
SHIF_RATE = Decimal("0.0275")
SHIF_MINIMUM = Decimal("300.00")

# --- Affordable Housing Levy ---
HOUSING_LEVY_RATE = Decimal("0.015")


def _round(value: Decimal) -> Decimal:
    return value.quantize(TWO_PLACES, rounding=ROUND_HALF_UP)


def calculate_nssf(gross_pay: Decimal) -> Decimal:
    """Employee NSSF contribution: 6% of pensionable pay up to the LEL (Tier I)
    plus 6% of pensionable pay between the LEL and UEL (Tier II)."""
    pensionable_pay = min(gross_pay, NSSF_UPPER_EARNINGS_LIMIT)
    tier_i = min(pensionable_pay, NSSF_LOWER_EARNINGS_LIMIT) * NSSF_RATE
    tier_ii_base = max(pensionable_pay - NSSF_LOWER_EARNINGS_LIMIT, Decimal("0"))
    tier_ii = tier_ii_base * NSSF_RATE
    return _round(tier_i + tier_ii)


def calculate_shif(gross_pay: Decimal) -> Decimal:
    """SHIF: 2.75% of gross salary, subject to a KES 300 minimum."""
    contribution = gross_pay * SHIF_RATE
    return _round(max(contribution, SHIF_MINIMUM))


def calculate_housing_levy(gross_pay: Decimal) -> Decimal:
    """Affordable Housing Levy: 1.5% of gross salary (employee share)."""
    return _round(gross_pay * HOUSING_LEVY_RATE)


def calculate_paye(taxable_income: Decimal) -> Decimal:
    """Progressive PAYE on taxable income (gross income less NSSF/SHIF/Housing
    Levy allowable deductions), before personal relief is applied."""
    remaining = taxable_income
    lower_bound = Decimal("0")
    tax = Decimal("0")
    for upper_bound, rate in PAYE_BANDS:
        if remaining <= 0:
            break
        if upper_bound is None:
            band_amount = remaining
        else:
            band_amount = min(remaining, upper_bound - lower_bound)
        if band_amount > 0:
            tax += band_amount * rate
            remaining -= band_amount
        lower_bound = upper_bound if upper_bound is not None else lower_bound
    return _round(tax)


@dataclass
class PayrollComputation:
    gross_pay: Decimal
    taxable_income: Decimal
    paye: Decimal
    personal_relief: Decimal
    nssf: Decimal
    shif: Decimal
    housing_levy: Decimal
    other_deductions: Decimal
    total_deductions: Decimal
    net_pay: Decimal


def compute_payslip(
    basic_salary: Decimal,
    allowances: Decimal = Decimal("0"),
    other_deductions: Decimal = Decimal("0"),
) -> PayrollComputation:
    """Compute a full payslip breakdown for one employee for one period.

    Order of operations (post-2024 Kenyan tax rules):
      1. Gross pay = basic salary + allowances
      2. NSSF, SHIF, Housing Levy are calculated on gross pay
      3. Taxable income = gross pay - (NSSF + SHIF + Housing Levy)
      4. PAYE is calculated on taxable income using the progressive bands
      5. Personal relief (KES 2,400/month) is subtracted from PAYE
      6. Net pay = gross pay - all statutory deductions - PAYE (after relief) - other deductions
    """
    gross_pay = basic_salary + allowances

    nssf = calculate_nssf(gross_pay)
    shif = calculate_shif(gross_pay)
    housing_levy = calculate_housing_levy(gross_pay)

    taxable_income = _round(gross_pay - nssf - shif - housing_levy)
    paye_before_relief = calculate_paye(taxable_income)
    paye = max(paye_before_relief - PERSONAL_RELIEF, Decimal("0"))
    paye = _round(paye)

    total_deductions = _round(nssf + shif + housing_levy + paye + other_deductions)
    net_pay = _round(gross_pay - total_deductions)

    return PayrollComputation(
        gross_pay=_round(gross_pay),
        taxable_income=taxable_income,
        paye=paye,
        personal_relief=PERSONAL_RELIEF,
        nssf=nssf,
        shif=shif,
        housing_levy=housing_levy,
        other_deductions=_round(other_deductions),
        total_deductions=total_deductions,
        net_pay=net_pay,
    )
