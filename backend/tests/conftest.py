import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.db.repositories import clear_repositories
from app.main import app


@pytest.fixture(autouse=True)
def isolate_backend_settings(monkeypatch):
    for name, value in {
        "REQUIRE_AUTH": "false",
        "SUPABASE_URL": "",
        "SUPABASE_SERVICE_KEY": "",
        "SUPABASE_JWT_SECRET": "",
    }.items():
        monkeypatch.setenv(name, value)
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def client(monkeypatch) -> TestClient:
    for name, value in {
        "REQUIRE_AUTH": "false",
        "SUPABASE_URL": "",
        "SUPABASE_SERVICE_KEY": "",
        "SUPABASE_JWT_SECRET": "",
    }.items():
        monkeypatch.setenv(name, value)
    get_settings.cache_clear()
    clear_repositories()
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    clear_repositories()
    get_settings.cache_clear()
