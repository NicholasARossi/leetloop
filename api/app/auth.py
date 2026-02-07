"""JWT authentication middleware for extension clients."""

import json
from dataclasses import dataclass
from functools import lru_cache
from typing import Optional

import httpx
import jwt
from fastapi import Header, HTTPException
from jwt import PyJWKClient

from app.config import get_settings


@dataclass
class AuthenticatedUser:
    id: str
    email: Optional[str]


@lru_cache(maxsize=1)
def _get_jwks_client() -> PyJWKClient:
    """Get cached JWKS client for Supabase."""
    settings = get_settings()
    jwks_url = f"{settings.supabase_url}/auth/v1/.well-known/jwks.json"
    return PyJWKClient(jwks_url, cache_keys=True)


def _decode_jwt(token: str) -> dict:
    """Decode and verify a Supabase JWT using JWKS (supports ES256)."""
    settings = get_settings()

    try:
        # Get the signing key from Supabase JWKS endpoint
        jwks_client = _get_jwks_client()
        signing_key = jwks_client.get_signing_key_from_jwt(token)

        return jwt.decode(
            token,
            signing_key.key,
            algorithms=["ES256", "HS256"],
            audience="authenticated",
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {e}")
    except Exception as e:
        # JWKS fetch failed - log and return helpful error
        raise HTTPException(status_code=500, detail=f"JWT verification failed: {e}")


def get_current_user(
    authorization: str = Header(...),
) -> AuthenticatedUser:
    """Extract and verify the authenticated user from the Authorization header."""
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")

    token = authorization[len("Bearer "):]
    payload = _decode_jwt(token)

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Token missing sub claim")

    return AuthenticatedUser(
        id=user_id,
        email=payload.get("email"),
    )


def get_optional_user(
    authorization: Optional[str] = Header(None),
) -> Optional[AuthenticatedUser]:
    """Extract user from Authorization header if present, otherwise return None."""
    if not authorization or not authorization.startswith("Bearer "):
        return None

    token = authorization[len("Bearer "):]
    try:
        payload = _decode_jwt(token)
    except HTTPException:
        return None

    user_id = payload.get("sub")
    if not user_id:
        return None

    return AuthenticatedUser(
        id=user_id,
        email=payload.get("email"),
    )
