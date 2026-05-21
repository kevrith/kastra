from contextlib import asynccontextmanager
from typing import Callable

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from starlette.types import ASGIApp, Receive, Scope, Send
import logging

logger = logging.getLogger(__name__)

from app.config import settings
from app.routers import auth, clients, dashboard, invoices, mpesa, organization, quotations, reports
from app.routers import pay, portal, paystack
from app.routers import expenses, products, notifications, search, invoice_payments, recurring_invoices
from app.routers import ocr, subscriptions, superadmin
from app.services.scheduler import start_scheduler, stop_scheduler
from app.utils.rate_limit import limiter


class SecurityHeadersMiddleware:
    """
    Pure ASGI middleware — adds security headers required by OWASP and the
    Kenya DPA 2019 data security obligations (Section 41 — security safeguards).
    Implemented as pure ASGI (not BaseHTTPMiddleware) to avoid event-loop
    conflicts with asyncpg under anyio.
    """

    _HEADERS = [
        (b"x-content-type-options", b"nosniff"),
        (b"x-frame-options", b"DENY"),
        (b"x-xss-protection", b"1; mode=block"),
        (b"referrer-policy", b"strict-origin-when-cross-origin"),
        (b"permissions-policy", b"camera=(), microphone=(), geolocation=()"),
        (b"cache-control", b"no-store"),
    ]
    _HSTS = (b"strict-transport-security", b"max-age=31536000; includeSubDomains; preload")

    def __init__(self, app: ASGIApp) -> None:
        self.app = app
        self._extra = list(self._HEADERS)
        if settings.is_production:
            self._extra.append(self._HSTS)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_with_headers(message: dict) -> None:
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                headers.extend(self._extra)
                message = {**message, "headers": headers}
            await send(message)

        await self.app(scope, receive, send_with_headers)


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.sentry_dsn:
        try:
            import sentry_sdk
            from sentry_sdk.integrations.starlette import StarletteIntegration
            from sentry_sdk.integrations.fastapi import FastApiIntegration
            sentry_sdk.init(
                dsn=settings.sentry_dsn,
                environment=settings.environment,
                integrations=[StarletteIntegration(), FastApiIntegration()],
                traces_sample_rate=0.2,
                send_default_pii=False,  # DPA compliance — no PII in error reports
            )
        except ImportError:
            pass

    start_scheduler()
    yield
    stop_scheduler()


app = FastAPI(
    title="Kastra Enterprises API",
    description="Business operations platform for Kenyan SMEs",
    version="1.0.0",
    docs_url="/docs" if not settings.is_production else None,
    redoc_url="/redoc" if not settings.is_production else None,
    lifespan=lifespan,
)

app.state.limiter = limiter
# CORS must be outermost so its headers survive even on unhandled 500s
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(SlowAPIMiddleware)


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        content={"error": "Too many requests", "detail": "Please wait before trying again."},
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled exception: %s", exc)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


app.include_router(auth.router)
app.include_router(organization.router)
app.include_router(clients.router)
app.include_router(quotations.router)
app.include_router(invoices.router)
app.include_router(invoice_payments.router)
app.include_router(mpesa.router)
app.include_router(dashboard.router)
app.include_router(reports.router)
app.include_router(pay.router)
app.include_router(portal.router)
app.include_router(paystack.router)
app.include_router(expenses.router)
app.include_router(products.router)
app.include_router(notifications.router)
app.include_router(search.router)
app.include_router(recurring_invoices.router)
app.include_router(ocr.router)
app.include_router(subscriptions.router)
app.include_router(superadmin.router)


@app.get("/health")
async def health():
    return {"status": "ok", "environment": settings.environment}
