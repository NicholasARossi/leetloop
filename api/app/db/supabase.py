"""Supabase client for database operations."""

from functools import lru_cache

from supabase import Client, create_client

from app.config import get_settings


@lru_cache
def get_supabase_client() -> Client:
    """Get cached Supabase client instance."""
    settings = get_settings()
    return create_client(settings.supabase_url, settings.supabase_anon_key)


def get_supabase_admin_client() -> Client:
    """Get Supabase client with service role key for admin operations."""
    settings = get_settings()
    if not settings.supabase_service_role_key:
        raise ValueError("SUPABASE_SERVICE_ROLE_KEY not configured")
    return create_client(settings.supabase_url, settings.supabase_service_role_key)


async def get_supabase() -> Client:
    """Dependency for getting Supabase client in routes."""
    return get_supabase_client()
