import uuid
from datetime import datetime, timezone
from urllib.parse import urlencode

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response, status
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.utils.rate_limit import limiter

from app.config import settings
from app.database import get_db
from app.dependencies import get_current_user, get_current_user_from_refresh
from app.models.user import User
from app.schemas.auth import (
    ChangePasswordRequest,
    ForgotPasswordRequest,
    LoginRequest,
    LoginResponse,
    TotpDisableRequest,
    TotpEnableRequest,
    TotpEnableResponse,
    TotpLoginRequest,
    TotpSetupResponse,
    TotpStatusResponse,
    RegisterRequest,
    ResendVerificationRequest,
    ResetPasswordRequest,
    TokenResponse,
    UserOut,
)
from app.services.audit_service import client_ip, log_for_user, log_independent
from app.services.totp_service import (
    consume_backup_code,
    generate_backup_codes,
    generate_secret,
    hash_backup_codes,
    provisioning_uri,
    qr_data_uri,
    remaining_backup_codes,
    verify_code,
)
from app.services.auth_service import (
    authenticate_user,
    create_user_with_org,
    get_google_user_info,
    get_or_create_google_user,
    get_user_by_email,
)
from app.services.email_service import (
    create_email_verification_token,
    create_password_reset_token,
    send_password_reset_email,
    send_verification_email,
    verify_email_verification_token,
    verify_password_reset_token,
)
from app.utils.security import (
    create_access_token,
    create_mfa_token,
    create_refresh_token,
    decode_mfa_token,
    decode_refresh_token,
    hash_password,
    verify_password,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_REDIRECT_URI = f"{settings.backend_url}/api/auth/google/callback"


def _set_refresh_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key="refresh_token",
        value=token,
        httponly=True,
        secure=settings.is_production,
        samesite="none" if settings.is_production else "lax",
        max_age=settings.refresh_token_expire_days * 86400,
    )


async def _load_user_with_org(db: AsyncSession, user_id) -> User:
    result = await db.execute(
        select(User).where(User.id == user_id).options(selectinload(User.organization))
    )
    return result.scalar_one()


@router.post("/register", status_code=status.HTTP_201_CREATED)
@limiter.limit("10/hour")
async def register(request: Request, payload: RegisterRequest, db: AsyncSession = Depends(get_db)):
    existing = await get_user_by_email(db, payload.email)
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")
    if len(payload.password) < 8:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Password must be at least 8 characters")
    if not payload.consent:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="You must accept the Privacy Policy and Terms of Service to register")
    if not payload.business_name.strip():
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Business name is required")

    user = await create_user_with_org(db, payload.email, payload.password, payload.display_name, payload.business_name.strip(), plan=payload.plan, referral_code=payload.referral_code)
    user.consented_at = datetime.now(timezone.utc)
    await db.commit()

    token = create_email_verification_token(payload.email)
    await send_verification_email(payload.email, token)

    return {"message": "Account created. Please check your email to activate your account."}


@router.get("/verify-email")
@limiter.limit("20/hour")
async def verify_email(request: Request, token: str, db: AsyncSession = Depends(get_db)):
    try:
        email = verify_email_verification_token(token)
    except JWTError:
        raise HTTPException(status_code=400, detail="INVALID_TOKEN")

    user = await get_user_by_email(db, email)
    if not user:
        raise HTTPException(status_code=400, detail="INVALID_TOKEN")

    if user.email_verified:
        raise HTTPException(status_code=409, detail="ALREADY_VERIFIED")

    user.email_verified = True
    user.last_login_at = datetime.now(timezone.utc)
    await db.commit()

    user = await _load_user_with_org(db, user.id)
    access_token = create_access_token(str(user.id), user.role)
    refresh_token = create_refresh_token(str(user.id), user.token_version)

    from fastapi.responses import JSONResponse
    resp = JSONResponse(content={"access_token": access_token})
    _set_refresh_cookie(resp, refresh_token)
    return resp


@router.post("/resend-verification")
@limiter.limit("5/hour")
async def resend_verification(request: Request, payload: ResendVerificationRequest, db: AsyncSession = Depends(get_db)):
    user = await get_user_by_email(db, payload.email)
    if user and not user.email_verified:
        token = create_email_verification_token(user.email)
        await send_verification_email(user.email, token)
    # Always return the same message — don't reveal whether email exists
    return {"message": "If that email is registered and unverified, a new activation link has been sent."}


@router.post("/login", response_model=LoginResponse)
@limiter.limit("20/minute;100/hour")
async def login(request: Request, payload: LoginRequest, response: Response, db: AsyncSession = Depends(get_db)):
    user = await authenticate_user(db, payload.email, payload.password)
    if not user:
        # Correlate the attempt to a real account where one exists, so the log
        # identifies the targeted user without storing the raw address.
        existing = (await db.execute(
            select(User).where(User.email == payload.email)
        )).scalar_one_or_none()
        await log_independent(
            db,
            action="login_failed",
            resource_type="auth",
            detail="Failed login — incorrect password."
                   if existing else "Failed login — no account for that email.",
            organization_id=str(existing.organization_id) if existing else None,
            user_id=str(existing.id) if existing else None,
            ip_address=client_ip(request),
        )
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    if not user.email_verified:
        await log_independent(
            db,
            action="login_failed",
            resource_type="auth",
            detail="Login blocked — email not verified.",
            organization_id=str(user.organization_id),
            user_id=str(user.id),
            ip_address=client_ip(request),
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="EMAIL_NOT_VERIFIED",
        )

    # Password is correct — but with 2FA on, that only earns a challenge.
    # No session cookie is set until the code checks out.
    if user.totp_enabled:
        await log_for_user(
            db, user, action="login", resource_type="auth",
            detail="Password accepted — awaiting two-factor code.", request=request,
        )
        return LoginResponse(mfa_required=True, mfa_token=create_mfa_token(str(user.id)))

    user.last_login_at = datetime.now(timezone.utc)
    await log_for_user(
        db, user, action="login", resource_type="auth",
        detail=f"Signed in as {user.role}.", request=request,
    )
    access_token = create_access_token(str(user.id), user.role)
    refresh_token = create_refresh_token(str(user.id), user.token_version)
    _set_refresh_cookie(response, refresh_token)
    return LoginResponse(access_token=access_token)


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(response: Response, user: User = Depends(get_current_user_from_refresh)):
    access_token = create_access_token(str(user.id), user.role)
    new_refresh = create_refresh_token(str(user.id), user.token_version)
    _set_refresh_cookie(response, new_refresh)
    return TokenResponse(access_token=access_token)


@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
    refresh_token: str = Cookie(default=None),
):
    if refresh_token:
        try:
            payload = decode_refresh_token(refresh_token)
            user_id = payload.get("sub")
            if user_id:
                result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
                user = result.scalar_one_or_none()
                if user:
                    user.token_version += 1
                    await log_for_user(
                        db, user, action="logout", resource_type="auth",
                        detail="Signed out — refresh tokens revoked.", request=request,
                    )
        except Exception:
            pass  # invalid token — still clear the cookie
    response.delete_cookie("refresh_token")
    return {"message": "Logged out"}


@router.get("/me", response_model=UserOut)
async def me(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await _load_user_with_org(db, current_user.id)


@router.post("/change-password")
async def change_password(
    payload: ChangePasswordRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not current_user.hashed_password:
        raise HTTPException(status_code=400, detail="Account uses Google login — no password to change")
    if not verify_password(payload.current_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    if len(payload.new_password) < 8:
        raise HTTPException(status_code=422, detail="New password must be at least 8 characters")
    current_user.hashed_password = hash_password(payload.new_password)
    await log_for_user(
        db, current_user, action="update", resource_type="auth",
        detail="Password changed.", request=request,
    )
    return {"message": "Password changed"}


@router.post("/forgot-password")
@limiter.limit("5/hour")
async def forgot_password(request: Request, payload: ForgotPasswordRequest, db: AsyncSession = Depends(get_db)):
    user = await get_user_by_email(db, payload.email)
    if user and user.hashed_password:  # only email/password accounts
        token = create_password_reset_token(user.email)
        await send_password_reset_email(user.email, token)
    # Always return the same message — don't reveal whether email exists
    return {"message": "If that email exists, a reset link has been sent"}


@router.post("/reset-password")
async def reset_password(payload: ResetPasswordRequest, db: AsyncSession = Depends(get_db)):
    try:
        email = verify_password_reset_token(payload.token)
    except JWTError:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")

    if len(payload.new_password) < 8:
        raise HTTPException(status_code=422, detail="Password must be at least 8 characters")

    user = await get_user_by_email(db, email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.hashed_password = hash_password(payload.new_password)
    return {"message": "Password reset successful"}


@router.get("/google")
async def google_login(plan: str = "free"):
    from app.utils.plan_limits import VALID_PLANS
    chosen_plan = plan if plan in VALID_PLANS else "free"
    params = {
        "client_id": settings.google_client_id,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "state": chosen_plan,
    }
    return {"auth_url": f"{GOOGLE_AUTH_URL}?{urlencode(params)}"}


@router.get("/google/callback")
async def google_callback(code: str, response: Response, db: AsyncSession = Depends(get_db), state: str = "free"):
    try:
        google_info = await get_google_user_info(code, GOOGLE_REDIRECT_URI)
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Google OAuth failed")

    user = await get_or_create_google_user(db, google_info, plan=state)
    user.last_login_at = datetime.now(timezone.utc)

    access_token = create_access_token(str(user.id), user.role)
    refresh_token = create_refresh_token(str(user.id), user.token_version)
    _set_refresh_cookie(response, refresh_token)

    from fastapi.responses import RedirectResponse
    return RedirectResponse(url=f"{settings.primary_frontend_url}/auth/callback?token={access_token}")


# ---------------------------------------------------------------------------
# Kenya Data Protection Act 2019 — Data Subject Rights
# ---------------------------------------------------------------------------

@router.get("/me/export")
async def export_my_data(current_user: User = Depends(get_current_user)):
    """
    Right to data portability — Kenya DPA 2019, Section 28.
    Returns all personal data held about the authenticated user.
    """
    return {
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "notice": "This export contains all personal data Kastra holds about you.",
        "user": {
            "id": str(current_user.id),
            "email": current_user.email,
            "display_name": current_user.display_name,
            "role": current_user.role,
            "created_at": current_user.created_at.isoformat(),
            "consented_at": current_user.consented_at.isoformat() if current_user.consented_at else None,
            "last_login_at": current_user.last_login_at.isoformat() if current_user.last_login_at else None,
        },
    }


@router.delete("/me")
async def delete_my_account(
    response: Response,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Right to erasure — Kenya DPA 2019, Section 26.
    PII is anonymised rather than hard-deleted to satisfy the Kenya Tax
    Procedures Act (5-year financial record retention requirement).
    All sessions are immediately invalidated.
    """
    current_user.email = f"deleted-{current_user.id}@deleted.invalid"
    current_user.display_name = "Deleted User"
    current_user.hashed_password = None
    current_user.google_id = None
    current_user.is_active = False
    current_user.token_version += 1  # invalidate all active sessions
    response.delete_cookie("refresh_token")
    return {
        "message": (
            "Your personal data has been anonymised. "
            "Financial transaction records are retained for 5 years as required by the Kenya Tax Procedures Act."
        )
    }


# ── Two-factor authentication ────────────────────────────────────────────────

@router.get("/2fa/status", response_model=TotpStatusResponse)
async def totp_status(current_user: User = Depends(get_current_user)):
    return TotpStatusResponse(
        enabled=current_user.totp_enabled,
        confirmed_at=current_user.totp_confirmed_at,
        backup_codes_remaining=remaining_backup_codes(current_user.totp_backup_codes),
    )


@router.post("/2fa/setup", response_model=TotpSetupResponse)
async def totp_setup(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Issue a fresh secret and the QR to scan.

    The secret is stored but NOT activated — `totp_enabled` only flips once a
    code from it has been verified, so an abandoned setup cannot lock anyone out.
    """
    if current_user.totp_enabled:
        raise HTTPException(status_code=400, detail="Two-factor authentication is already enabled")

    secret = generate_secret()
    current_user.totp_secret = secret
    uri = provisioning_uri(secret, current_user.email)
    await log_for_user(
        db, current_user, action="update", resource_type="auth",
        detail="Started two-factor setup.", request=request,
    )
    return TotpSetupResponse(secret=secret, otpauth_uri=uri, qr_data_uri=qr_data_uri(uri))


@router.post("/2fa/enable", response_model=TotpEnableResponse)
async def totp_enable(
    payload: TotpEnableRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Confirm the app is set up correctly, then turn 2FA on."""
    if current_user.totp_enabled:
        raise HTTPException(status_code=400, detail="Two-factor authentication is already enabled")
    if not current_user.totp_secret:
        raise HTTPException(status_code=400, detail="Start setup first")
    if not verify_code(current_user.totp_secret, payload.code):
        raise HTTPException(status_code=400, detail="That code is not valid. Check your authenticator app and try again.")

    codes = generate_backup_codes()
    current_user.totp_enabled = True
    current_user.totp_confirmed_at = datetime.now(timezone.utc)
    current_user.totp_backup_codes = hash_backup_codes(codes)
    # Existing sessions elsewhere predate 2FA, so retire them.
    current_user.token_version += 1

    await log_for_user(
        db, current_user, action="update", resource_type="auth",
        detail="Enabled two-factor authentication; other sessions revoked.", request=request,
    )
    # The only time the plaintext codes ever leave the server.
    return TotpEnableResponse(backup_codes=codes)


@router.post("/2fa/disable")
async def totp_disable(
    payload: TotpDisableRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Turn 2FA off. Requires the password, so a borrowed session is not enough."""
    if not current_user.totp_enabled:
        raise HTTPException(status_code=400, detail="Two-factor authentication is not enabled")
    if not current_user.hashed_password or not verify_password(payload.password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Password is incorrect")
    if payload.code and not verify_code(current_user.totp_secret, payload.code):
        raise HTTPException(status_code=400, detail="That code is not valid")

    current_user.totp_enabled = False
    current_user.totp_secret = None
    current_user.totp_confirmed_at = None
    current_user.totp_backup_codes = None
    await log_for_user(
        db, current_user, action="update", resource_type="auth",
        detail="Disabled two-factor authentication.", request=request,
    )
    return {"message": "Two-factor authentication disabled"}


@router.post("/2fa/verify-login", response_model=TokenResponse)
@limiter.limit("10/minute;40/hour")
async def totp_verify_login(
    request: Request,
    payload: TotpLoginRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """Exchange the challenge token plus a code for a real session."""
    try:
        claims = decode_mfa_token(payload.mfa_token)
    except Exception:
        raise HTTPException(status_code=401, detail="This sign-in attempt expired. Please log in again.")

    user = (await db.execute(
        select(User).where(User.id == uuid.UUID(claims["sub"]))
    )).scalar_one_or_none()
    if not user or not user.totp_enabled:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    used_backup = False
    if not verify_code(user.totp_secret, payload.code):
        matched, remaining = consume_backup_code(user.totp_backup_codes, payload.code)
        if not matched:
            await log_independent(
                db,
                action="login_failed",
                resource_type="auth",
                detail="Two-factor code rejected.",
                organization_id=str(user.organization_id),
                user_id=str(user.id),
                ip_address=client_ip(request),
            )
            raise HTTPException(status_code=401, detail="That code is not valid")
        user.totp_backup_codes = remaining
        used_backup = True

    user.last_login_at = datetime.now(timezone.utc)
    await log_for_user(
        db, user, action="login", resource_type="auth",
        detail=(
            f"Signed in as {user.role} using a recovery code "
            f"({remaining_backup_codes(user.totp_backup_codes)} left)."
            if used_backup else
            f"Signed in as {user.role} with two-factor."
        ),
        request=request,
    )
    access_token = create_access_token(str(user.id), user.role)
    _set_refresh_cookie(response, create_refresh_token(str(user.id), user.token_version))
    return TokenResponse(access_token=access_token)
