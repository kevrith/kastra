from slowapi import Limiter
from slowapi.util import get_remote_address

from app.config import settings

# Key function: use real client IP (works behind Render's proxy).
# Storage: in-memory by default (single instance); set REDIS_URL to share
# counters across instances/workers and survive restarts.
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[],
    storage_uri=settings.redis_url or "memory://",
)
