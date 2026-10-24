import pytest
from app.core.config import get_settings
from app.db.repositories import clear_repositories
from app.main import app
from fastapi.testclient import TestClient


@pytest.fixture
def client(monkeypatch) -> TestClient:
    monkeypatch.setenv("REQUIRE_AUTH", "false")
    get_settings.cache_clear()
    clear_repositories()
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    clear_repositories()
    get_settings.cache_clear()
