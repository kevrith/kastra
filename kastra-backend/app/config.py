from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Insecure shipped defaults — the app must refuse to start in production
# while any of these are still in effect.
_PLACEHOLDER_SECRETS = {
    "secret_key": "change-me-in-production",
    "refresh_secret_key": "change-me-refresh-in-production",
    "superadmin_password": "change-me-superadmin",
    "superadmin_secret_key": "change-me-superadmin-secret",
}
_MIN_SECRET_LENGTH = 32


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Database
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/kastra"

    @property
    def async_database_url(self) -> str:
        """Normalise the URL for asyncpg (handles Neon/Render connection strings)."""
        url = self.database_url
        # Convert postgres:// or postgresql:// → postgresql+asyncpg://
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql+asyncpg://", 1)
        elif url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        # asyncpg uses ?ssl=require, not ?sslmode=require
        url = url.replace("sslmode=require", "ssl=require")
        return url

    # JWT
    secret_key: str = "change-me-in-production"
    refresh_secret_key: str = "change-me-refresh-in-production"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 30

    # Google OAuth
    google_client_id: str = ""
    google_client_secret: str = ""

    # App — comma-separated list of allowed origins, e.g. "https://kastra-ten.vercel.app,https://app.kastra.co.ke"
    frontend_url: str = "http://localhost:5200"
    backend_url: str = "http://localhost:8080"
    environment: str = "development"

    @property
    def allowed_origins(self) -> list[str]:
        return [o.strip() for o in self.frontend_url.split(",") if o.strip()]

    @property
    def primary_frontend_url(self) -> str:
        return self.allowed_origins[0] if self.allowed_origins else self.frontend_url

    # M-Pesa
    mpesa_consumer_key: str = ""
    mpesa_consumer_secret: str = ""
    mpesa_shortcode: str = "174379"
    mpesa_passkey: str = ""
    mpesa_callback_url: str = "https://api.kastra.co.ke/api/mpesa/callback"
    mpesa_env: str = "sandbox"

    # Email
    sendgrid_api_key: str = ""
    mail_from: str = "noreply@kastra.co.ke"
    mail_reply_to: str = ""

    # Paystack card payments (set real keys in production)
    paystack_secret_key: str = "sk_test_placeholder"
    paystack_public_key: str = "pk_test_placeholder"

    # Affiliate programme
    affiliate_commission_ksh: int = 50  # KSh per active paying org per month — set AFFILIATE_COMMISSION_KSH to override

    # Africa's Talking (SMS + WhatsApp)
    at_api_key: str = ""
    at_username: str = "sandbox"   # "sandbox" for testing, your AT username for production
    at_sender_id: str = ""         # optional branded sender ID (must be pre-approved by AT)
    at_whatsapp_number: str = ""   # your AT-registered WhatsApp Business number e.g. +254700000000

    # Anthropic (Claude Vision for OCR scanning)
    anthropic_api_key: str = ""

    # Cloudinary (photo storage)
    cloudinary_cloud_name: str = ""
    cloudinary_api_key: str = ""
    cloudinary_api_secret: str = ""

    # Field-level encryption key — generate with:
    #   python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    # Set FIELD_ENCRYPTION_KEY in .env. If blank, credentials are stored plain-text (dev only).
    field_encryption_key: str = ""

    # Error tracking (optional — set SENTRY_DSN in production)
    sentry_dsn: str = ""

    # Super admin (separate credentials, never linked to org accounts)
    superadmin_username: str = "superadmin"
    superadmin_password: str = "change-me-superadmin"
    superadmin_secret_key: str = "change-me-superadmin-secret"

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @model_validator(mode="after")
    def _require_real_secrets_in_production(self) -> "Settings":
        if not self.is_production:
            return self
        problems = []
        for field, placeholder in _PLACEHOLDER_SECRETS.items():
            value = getattr(self, field)
            if not value or value == placeholder:
                problems.append(f"{field.upper()} is unset or still the shipped placeholder")
        for field in ("secret_key", "refresh_secret_key", "superadmin_secret_key"):
            if len(getattr(self, field)) < _MIN_SECRET_LENGTH:
                problems.append(f"{field.upper()} must be at least {_MIN_SECRET_LENGTH} characters")
        if self.secret_key == self.refresh_secret_key:
            problems.append("SECRET_KEY and REFRESH_SECRET_KEY must differ")
        if problems:
            raise ValueError(
                "Refusing to start in production with insecure configuration:\n  - "
                + "\n  - ".join(problems)
            )
        return self

    @property
    def mpesa_base_url(self) -> str:
        if self.mpesa_env == "production":
            return "https://api.safaricom.co.ke"
        return "https://sandbox.safaricom.co.ke"


settings = Settings()
