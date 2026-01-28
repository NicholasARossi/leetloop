"""Auth router for extension token management."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.auth import AuthenticatedUser, get_current_user
from app.db.supabase import get_supabase_admin_client

router = APIRouter()


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    expires_in: int
    token_type: str = "bearer"


class MigrateRequest(BaseModel):
    guest_id: str


class MigrateResponse(BaseModel):
    success: bool
    migrated: Optional[dict] = None
    error: Optional[str] = None


class MeResponse(BaseModel):
    id: str
    email: Optional[str] = None


@router.post("/auth/refresh", response_model=TokenResponse)
async def refresh_token(body: RefreshRequest) -> TokenResponse:
    """Refresh an expired access token using a refresh token.

    No auth required since the access token is expired.
    Proxies to the Supabase GoTrue refresh endpoint.
    """
    import httpx
    from app.config import get_settings

    settings = get_settings()
    url = f"{settings.supabase_url}/auth/v1/token?grant_type=refresh_token"

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                url,
                json={"refresh_token": body.refresh_token},
                headers={
                    "apikey": settings.supabase_anon_key,
                    "Content-Type": "application/json",
                },
            )

        if resp.status_code != 200:
            detail = resp.text
            try:
                detail = resp.json().get("error_description", resp.text)
            except Exception:
                pass
            raise HTTPException(status_code=401, detail=f"Refresh failed: {detail}")

        data = resp.json()
        return TokenResponse(
            access_token=data["access_token"],
            refresh_token=data["refresh_token"],
            expires_in=data.get("expires_in", 3600),
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Refresh error: {e}")


@router.post("/auth/migrate", response_model=MigrateResponse)
async def migrate_guest_data(
    body: MigrateRequest,
    user: AuthenticatedUser = Depends(get_current_user),
) -> MigrateResponse:
    """Migrate guest data to the authenticated user.

    Calls the migrate_guest_to_auth RPC on Supabase using the admin client.
    """
    try:
        admin = get_supabase_admin_client()
        result = admin.rpc("migrate_guest_to_auth", {
            "p_guest_id": body.guest_id,
            "p_auth_id": user.id,
        }).execute()

        if result.data and isinstance(result.data, dict):
            return MigrateResponse(
                success=result.data.get("success", False),
                migrated=result.data.get("migrated"),
                error=result.data.get("error"),
            )

        return MigrateResponse(success=True, migrated=result.data)
    except Exception as e:
        print(f"[Auth] Migration error: {e}")
        return MigrateResponse(success=False, error=str(e))


@router.get("/auth/me", response_model=MeResponse)
async def get_me(
    user: AuthenticatedUser = Depends(get_current_user),
) -> MeResponse:
    """Return the current user info from the JWT."""
    return MeResponse(id=user.id, email=user.email)
