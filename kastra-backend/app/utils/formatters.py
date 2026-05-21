from decimal import Decimal


def format_ksh(amount: Decimal) -> str:
    return f"KSh {amount:,.2f}"


def format_phone_display(phone: str) -> str:
    """Convert 254712345678 → +254 712 345 678"""
    if phone.startswith("254") and len(phone) == 12:
        return f"+{phone[:3]} {phone[3:6]} {phone[6:9]} {phone[9:]}"
    return phone
