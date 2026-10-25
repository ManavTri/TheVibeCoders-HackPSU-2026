import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.db.repositories import clear_repositories
from app.main import app
from app.services.ai.agent import reset_chat_state
from app.services.validation import engine
from app.services.validation.rules.base import ValidationConfig


@pytest.fixture(autouse=True)
def isolate_backend_settings(monkeypatch):
    for name, value in {
        "REQUIRE_AUTH": "false",
        "SUPABASE_URL": "",
        "SUPABASE_SERVICE_KEY": "",
        "SUPABASE_JWT_SECRET": "",
        "LLM_API_KEY": "",
        "LLM_MODEL": "",
        "RULE_ASSIST_ENABLED": "false",
    }.items():
        monkeypatch.setenv(name, value)
    get_settings.cache_clear()
    monkeypatch.setattr(
        engine,
        "_default_validation_config",
        lambda: ValidationConfig(strict=True),
    )
    reset_chat_state()
    yield
    reset_chat_state()
    get_settings.cache_clear()


@pytest.fixture
def client(monkeypatch) -> TestClient:
    for name, value in {
        "REQUIRE_AUTH": "false",
        "SUPABASE_URL": "",
        "SUPABASE_SERVICE_KEY": "",
        "SUPABASE_JWT_SECRET": "",
        "LLM_API_KEY": "",
        "LLM_MODEL": "",
        "RULE_ASSIST_ENABLED": "false",
    }.items():
        monkeypatch.setenv(name, value)
    get_settings.cache_clear()
    clear_repositories()
    reset_chat_state()
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    clear_repositories()
    reset_chat_state()
    get_settings.cache_clear()
