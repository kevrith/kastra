import os

from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy import Text
from sqlalchemy.types import TypeDecorator

_fernet: Fernet | None = None


def _get_fernet() -> Fernet | None:
    global _fernet
    if _fernet is not None:
        return _fernet
    raw = os.environ.get("FIELD_ENCRYPTION_KEY", "").strip()
    if not raw:
        return None
    _fernet = Fernet(raw.encode())
    return _fernet


def encrypt_value(plaintext: str) -> str:
    """Encrypt a string. Returns the original if no key is configured."""
    f = _get_fernet()
    if f is None:
        return plaintext
    return f.encrypt(plaintext.encode()).decode()


def decrypt_value(token: str) -> str:
    """Decrypt a Fernet token. Falls back to returning the raw value if decryption fails
    (handles plain-text values stored before encryption was enabled)."""
    f = _get_fernet()
    if f is None:
        return token
    try:
        return f.decrypt(token.encode()).decode()
    except (InvalidToken, Exception):
        return token


class EncryptedString(TypeDecorator):
    """SQLAlchemy column type that transparently encrypts on write and decrypts on read."""

    impl = Text
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        return encrypt_value(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return decrypt_value(value)
