from functools import lru_cache

from app.core.config import get_settings
from supabase import Client, create_client


@lru_cache
def get_supabase_client() -> Client | None:
    settings = get_settings()
    if not settings.supabase_url and not settings.supabase_service_key:
        return None
    if not settings.supabase_url or not settings.supabase_service_key:
        raise RuntimeError("SUPABASE_URL and SUPABASE_SERVICE_KEY must be configured together.")
    return create_client(settings.supabase_url, settings.supabase_service_key)
