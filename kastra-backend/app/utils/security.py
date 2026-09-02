from datetime import datetime, timedelta, timezone

import bcrypt
from jose import JWTError, jwt

from app.config import settings


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def create_access_token(subject: str, role: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    return jwt.encode(
        {"sub": subject, "role": role, "exp": expire, "type": "access"},
        settings.secret_key,
        algorithm="HS256",
    )


def create_refresh_token(subject: str, version: int = 0) -> str:
    expire = datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days)
    return jwt.encode(
        {"sub": subject, "exp": expire, "type": "refresh", "ver": version},
        settings.refresh_secret_key,
        algorithm="HS256",
    )


def create_mfa_token(subject: str) -> str:
    """Short-lived proof that a password check passed, pending a TOTP code.

    Deliberately a *different* token type from `access`, so a half-finished
    login can never be used as a session — decode_access_token rejects it.
    """
    expire = datetime.now(timezone.utc) + timedelta(minutes=5)
    return jwt.encode(
        {"sub": subject, "exp": expire, "type": "mfa"},
        settings.secret_key,
        algorithm="HS256",
    )


def decode_mfa_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
        if payload.get("type") != "mfa":
            raise JWTError("Invalid token type")
        return payload
    except JWTError:
        raise


def decode_access_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
        if payload.get("type") != "access":
            raise JWTError("Invalid token type")
        return payload
    except JWTError:
        raise


def decode_refresh_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, settings.refresh_secret_key, algorithms=["HS256"])
        if payload.get("type") != "refresh":
            raise JWTError("Invalid token type")
        return payload
    except JWTError:
        raise
