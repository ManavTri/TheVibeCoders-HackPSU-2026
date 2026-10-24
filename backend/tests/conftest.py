import pytest
from app.db.repositories import clear_reports
from app.main import app
from fastapi.testclient import TestClient


@pytest.fixture
def client() -> TestClient:
    clear_reports()
    return TestClient(app)
