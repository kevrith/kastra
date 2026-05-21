from pydantic_settings import BaseSettings, SettingsConfigDict


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

    # App
    frontend_url: str = "http://localhost:5200"
    backend_url: str = "http://localhost:8080"
    environment: str = "development"

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

    # Paystack card payments (set real keys in production)
    paystack_secret_key: str = "sk_test_placeholder"
    paystack_public_key: str = "pk_test_placeholder"

    # Anthropic (Claude Vision for OCR scanning)
    anthropic_api_key: str = ""

    # Error tracking (optional — set SENTRY_DSN in production)
    sentry_dsn: str = ""

    # Super admin (separate credentials, never linked to org accounts)
    superadmin_username: str = "superadmin"
    superadmin_password: str = "change-me-superadmin"
    superadmin_secret_key: str = "change-me-superadmin-secret"

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def mpesa_base_url(self) -> str:
        if self.mpesa_env == "production":
            return "https://api.safaricom.co.ke"
        return "https://sandbox.safaricom.co.ke"


settings = Settings()
