from slowapi import Limiter
from slowapi.util import get_remote_address

# Key function: use real client IP (works behind Render's proxy)
limiter = Limiter(key_func=get_remote_address, default_limits=[])
