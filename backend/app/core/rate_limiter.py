"""
app/core/rate_limiter.py
────────────────────────
SlowAPI Limiter initialization and user-specific key generator.
"""

from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address


def get_user_or_ip_limit_key(request: Request) -> str:
    """
    Identifies the unique rate limit key.
    Uses the authenticated User ID (from JWT sub) if present,
    otherwise falls back to the client's remote IP address.
    """
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
        try:
            from jose import jwt
            from app.core.config import settings
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            user_id = payload.get("sub")
            if user_id:
                return f"user:{user_id}"
        except Exception:
            pass

    return get_remote_address(request)


import os
import sys

# Shared limiter instance
# Automatically disabled during pytest runs to avoid unexpected 429s in other tests
is_testing = "pytest" in sys.modules or os.getenv("APP_ENV") == "testing"
limiter = Limiter(key_func=get_user_or_ip_limit_key, enabled=not is_testing)
