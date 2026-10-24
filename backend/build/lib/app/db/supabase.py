import threading

from app.core.config import get_settings
from supabase import Client, create_client

# FastAPI runs sync routes on a thread pool. One shared client means one shared
# HTTP/2 connection, and concurrent reads on it fail with httpx.ReadError.
# Giving each worker thread its own client gives each its own connections.
_local = threading.local()


def get_supabase_client() -> Client | None:
    settings = get_settings()
    if not settings.supabase_url and not settings.supabase_service_key:
        return None
    if not settings.supabase_url or not settings.supabase_service_key:
        raise RuntimeError("SUPABASE_URL and SUPABASE_SERVICE_KEY must be configured together.")
    client = getattr(_local, "client", None)
    if client is None:
        client = create_client(settings.supabase_url, settings.supabase_service_key)
        _local.client = client
    return client