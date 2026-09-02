"""Two-factor authentication (TOTP, RFC 6238) — secrets, QR provisioning, verification.

Kastra holds M-Pesa and Paystack credentials and can move real money, so a
stolen password must not be enough on its own. This implements the standard
authenticator-app flow: a shared secret, a 6-digit rolling code, and one-shot
recovery codes for the phone-in-a-matatu case.
"""
import base64
import hashlib
import io
import secrets

import pyotp
import qrcode

# One step either side of the current window, i.e. codes stay valid for ~90s.
# Enough for clock drift on a cheap handset without meaningfully widening the
# window an attacker can guess in.
_VALID_WINDOW = 1

_BACKUP_CODE_COUNT = 10


def generate_secret() -> str:
    """A fresh base32 TOTP secret."""
    return pyotp.random_base32()


def provisioning_uri(secret: str, email: str, issuer: str = "Kastra") -> str:
    """The otpauth:// URI an authenticator app scans."""
    return pyotp.TOTP(secret).provisioning_uri(name=email, issuer_name=issuer)


def qr_data_uri(uri: str) -> str:
    """The provisioning URI as an inline PNG, so the API needs no static host."""
    img = qrcode.make(uri)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def verify_code(secret: str, code: str) -> bool:
    """True if `code` is valid for `secret` right now."""
    if not secret or not code:
        return False
    return pyotp.TOTP(secret).verify(code.strip().replace(" ", ""), valid_window=_VALID_WINDOW)


# ── Recovery codes ───────────────────────────────────────────────────────────

def generate_backup_codes(count: int = _BACKUP_CODE_COUNT) -> list[str]:
    """Human-transcribable one-time codes, shown to the user exactly once."""
    return [f"{secrets.token_hex(2)}-{secrets.token_hex(2)}" for _ in range(count)]


def _hash_code(code: str) -> str:
    return hashlib.sha256(code.strip().lower().encode()).hexdigest()


def hash_backup_codes(codes: list[str]) -> str:
    return "\n".join(_hash_code(c) for c in codes)


def consume_backup_code(stored: str | None, code: str) -> tuple[bool, str | None]:
    """Check a recovery code and burn it.

    Returns (matched, remaining_hashes). A code works once — on a match the
    hash is dropped, so replaying it fails even if someone watched it typed.
    """
    if not stored or not code:
        return False, stored
    wanted = _hash_code(code)
    hashes = [h for h in stored.splitlines() if h]
    if wanted not in hashes:
        return False, stored
    hashes.remove(wanted)
    return True, "\n".join(hashes)


def remaining_backup_codes(stored: str | None) -> int:
    return len([h for h in (stored or "").splitlines() if h])
