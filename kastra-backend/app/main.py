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
from app.routers import ocr, subscriptions, superadmin, team, projects
from app.routers import suppliers, supplier_portal
from app.routers import ai as ai_router
from app.routers import currency
from app.routers import employees, payroll
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

        is_health = scope.get("path") == "/health"

        async def send_with_headers(message: dict) -> None:
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                for key, val in self._extra:
                    if is_health and key == b"cache-control":
                        continue
                    headers.append((key, val))
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
                send_default_pii=False,
            )
        except ImportError:
            pass

    # Backfill products from existing quotation/invoice items (idempotent upsert)
    try:
        from app.database import AsyncSessionLocal
        from app.models.product import Product
        from sqlalchemy import text
        from sqlalchemy.dialects.postgresql import insert as pg_insert
        import uuid as _uuid
        from decimal import Decimal as _Decimal

        async with AsyncSessionLocal() as db:
            rows = (await db.execute(text("""
                SELECT description, unit_price, organization_id FROM (
                    SELECT qi.description, qi.unit_price, q.organization_id
                    FROM quotation_items qi JOIN quotations q ON q.id = qi.quotation_id
                    UNION ALL
                    SELECT ii.description, ii.unit_price, i.organization_id
                    FROM invoice_items ii JOIN invoices i ON i.id = ii.invoice_id
                ) src
            """))).all()
            catalog: dict[tuple, _Decimal] = {}
            for desc, price, org_id in rows:
                catalog[(str(org_id), desc)] = _Decimal(str(price))
            for (org_id, name), unit_price in catalog.items():
                await db.execute(
                    pg_insert(Product).values(
                        id=_uuid.uuid4(), organization_id=org_id,
                        name=name, unit_price=unit_price,
                    ).on_conflict_do_update(
                        index_elements=["organization_id", "name"],
                        set_={"unit_price": unit_price},
                    )
                )
            await db.commit()
            logger.info("Products backfill: %d entries synced", len(catalog))
    except Exception:
        logger.exception("Products backfill failed (non-fatal)")

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
# Middlewares are applied in reverse order — last added = outermost (runs first).
# CORSMiddleware must be outermost so CORS headers survive even on 500s.
app.add_middleware(SlowAPIMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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
app.include_router(team.router)
app.include_router(projects.router)
app.include_router(suppliers.router)
app.include_router(supplier_portal.router)
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
app.include_router(ai_router.router)
app.include_router(currency.router)
app.include_router(employees.router)
app.include_router(payroll.router)
app.include_router(subscriptions.router)
app.include_router(superadmin.router)


@app.api_route("/health", methods=["GET", "HEAD"])
async def health():
    return {"status": "ok", "environment": settings.environment}
