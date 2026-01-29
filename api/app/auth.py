"""JWT authentication middleware for extension clients."""

from dataclasses import dataclass
from typing import Optional

import jwt
from fastapi import Header, HTTPException

from app.config import get_settings


@dataclass
class AuthenticatedUser:
    id: str
    email: Optional[str]


def _decode_jwt(token: str) -> dict:
    """Decode and verify a Supabase JWT."""
    settings = get_settings()
    secret = settings.supabase_jwt_secret
    if not secret:
        raise HTTPException(status_code=500, detail="JWT secret not configured")

    try:
        return jwt.decode(
            token,
            secret,
            algorithms=["HS256"],
            audience="authenticated",
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {e}")


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
