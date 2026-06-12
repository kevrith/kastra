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
    RegisterRequest,
    ResendVerificationRequest,
    ResetPasswordRequest,
    TokenResponse,
    UserOut,
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
from app.utils.security import create_access_token, create_refresh_token, decode_refresh_token, hash_password, verify_password

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


@router.post("/login", response_model=TokenResponse)
@limiter.limit("20/minute;100/hour")
async def login(request: Request, payload: LoginRequest, response: Response, db: AsyncSession = Depends(get_db)):
    user = await authenticate_user(db, payload.email, payload.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    if not user.email_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="EMAIL_NOT_VERIFIED",
        )

    user.last_login_at = datetime.now(timezone.utc)
    access_token = create_access_token(str(user.id), user.role)
    refresh_token = create_refresh_token(str(user.id), user.token_version)
    _set_refresh_cookie(response, refresh_token)
    return TokenResponse(access_token=access_token)


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(response: Response, user: User = Depends(get_current_user_from_refresh)):
    access_token = create_access_token(str(user.id), user.role)
    new_refresh = create_refresh_token(str(user.id), user.token_version)
    _set_refresh_cookie(response, new_refresh)
    return TokenResponse(access_token=access_token)


@router.post("/logout")
async def logout(
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
    current_user: User = Depends(get_current_user),
):
    if not current_user.hashed_password:
        raise HTTPException(status_code=400, detail="Account uses Google login — no password to change")
    if not verify_password(payload.current_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    if len(payload.new_password) < 8:
        raise HTTPException(status_code=422, detail="New password must be at least 8 characters")
    current_user.hashed_password = hash_password(payload.new_password)
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
