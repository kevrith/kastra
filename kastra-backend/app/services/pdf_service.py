"""
Server-side PDF generation using Playwright + Jinja2.
Renders invoice/quotation data into a self-contained HTML document,
then prints it to PDF via headless Chromium.
"""
import io
import math
from pathlib import Path

import qrcode
import qrcode.image.svg
from jinja2 import Environment, FileSystemLoader, select_autoescape
from playwright.async_api import async_playwright

_TEMPLATES_DIR = Path(__file__).parent.parent / "templates"
_KRA_VERIFY_URL = "https://etims.kra.go.ke/etims-portal/searchDetails/"

_jinja_env = Environment(
    loader=FileSystemLoader(str(_TEMPLATES_DIR)),
    autoescape=select_autoescape(["html"]),
)


def _ksh_filter(val) -> str:
    try:
        return f"KSh {float(val):,.2f}"
    except (TypeError, ValueError):
        return "KSh 0.00"


def _fmtdate_filter(val) -> str:
    if val is None:
        return "—"
    try:
        from datetime import datetime
        if isinstance(val, str):
            val = datetime.fromisoformat(val)
        return val.strftime("%-d %b %Y")
    except Exception:
        return str(val)


_jinja_env.filters["ksh"] = _ksh_filter
_jinja_env.filters["fmtdate"] = _fmtdate_filter


def _org_initials(org_name: str) -> str:
    parts = (org_name or "B").split()
    return "".join(w[0] for w in parts if w)[:2].upper()


def _make_qr_svg(cu_invoice_no: str) -> str:
    url = f"{_KRA_VERIFY_URL}{cu_invoice_no}"
    factory = qrcode.image.svg.SvgPathImage
    img = qrcode.make(url, image_factory=factory, box_size=4, border=1)
    buf = io.BytesIO()
    img.save(buf)
    svg = buf.getvalue().decode("utf-8")
    # Strip XML declaration and set fixed size
    svg = svg.replace('<?xml version=\'1.0\' encoding=\'UTF-8\'?>\n', "")
    svg = svg.replace("<svg ", '<svg width="72" height="72" ')
    return svg


def _status_colors(doc_type: str, doc) -> dict:
    if doc_type == "invoice":
        status = doc.get("payment_status", "unpaid")
        return {
            "paid":    {"bg": "#dcfce7", "text": "#15803d"},
            "partial": {"bg": "#ffedd5", "text": "#c2410c"},
            "unpaid":  {"bg": "#fee2e2", "text": "#b91c1c"},
        }.get(status, {"bg": "#f3f4f6", "text": "#374151"})
    else:
        status = doc.get("status", "draft")
        return {
            "accepted": {"bg": "#dcfce7", "text": "#15803d"},
            "pending":  {"bg": "#ffedd5", "text": "#c2410c"},
            "declined": {"bg": "#fee2e2", "text": "#b91c1c"},
            "expired":  {"bg": "#fee2e2", "text": "#b91c1c"},
            "draft":    {"bg": "#f3f4f6", "text": "#374151"},
        }.get(status, {"bg": "#f3f4f6", "text": "#374151"})


def _build_context(doc_type: str, doc: dict, org: dict) -> dict:
    status_label = doc.get("payment_status") if doc_type == "invoice" else doc.get("status")
    status_color = _status_colors(doc_type, doc)

    grand_total = float(doc.get("grand_total", 0))
    amount_paid = float(doc.get("amount_paid", 0))
    balance_due = max(0.0, grand_total - amount_paid)
    paid_pct = math.floor((amount_paid / grand_total * 100)) if grand_total else 0

    qr_svg = None
    if doc_type == "invoice" and doc.get("etims_cu_invoice_no"):
        try:
            qr_svg = _make_qr_svg(doc["etims_cu_invoice_no"])
        except Exception:
            pass

    return {
        "doc_type": doc_type,
        "doc": doc,
        "org": org,
        "org_initials": _org_initials(org.get("name", "")),
        "status_label": status_label,
        "status_color": status_color,
        "balance_due": balance_due,
        "paid_pct": paid_pct,
        "qr_svg": qr_svg,
    }


def render_html(doc_type: str, doc: dict, org: dict) -> str:
    ctx = _build_context(doc_type, doc, org)
    template = _jinja_env.get_template("document.html")
    return template.render(**ctx)


async def html_to_pdf(html: str) -> bytes:
    async with async_playwright() as pw:
        browser = await pw.chromium.launch()
        page = await browser.new_page()
        await page.set_content(html, wait_until="networkidle")
        pdf_bytes = await page.pdf(
            format="A4",
            print_background=True,
            margin={"top": "10mm", "bottom": "12mm", "left": "0", "right": "0"},
        )
        await browser.close()
    return pdf_bytes


async def generate_pdf(doc_type: str, doc: dict, org: dict) -> bytes:
    html = render_html(doc_type, doc, org)
    return await html_to_pdf(html)
