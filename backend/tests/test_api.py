import jwt
from app.core.config import Settings


def test_health(client) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_report_and_insights_flow(client) -> None:
    documents = [
        {
            "id": "award-1",
            "filename": "award_letter.pdf",
            "document_type": "award_letter",
            "amount": "12000",
            "term": "Fall 2026",
            "deadline": "2026-07-15",
            "required_credits": 12,
        },
        {
            "id": "bill-1",
            "filename": "tuition_bill.pdf",
            "document_type": "tuition_bill",
            "amount": "18000",
            "term": "Spring 2026",
            "deadline": "2026-08-01",
            "required_credits": 6,
        },
    ]
    created = client.post("/api/validations", json=documents)
    assert created.status_code == 201
    report = created.json()
    assert report["findings"]
    assert client.get(f"/api/validations/{report['id']}").status_code == 200
    insights = client.get(f"/api/insights/{report['id']}").json()
    assert insights["report_id"] == report["id"]
    assert insights["recommendations"]


def test_validation_requires_two_documents(client) -> None:
    response = client.post("/api/validations", json=[])
    assert response.status_code == 400


def test_missing_report_returns_404(client) -> None:
    assert client.get("/api/validations/not-a-report").status_code == 404


def test_supabase_hs256_authentication_is_enforced(client, monkeypatch) -> None:
    secret = "test-secret-for-hs256-key-long-enough"
    settings = Settings(require_auth=True, supabase_jwt_secret=secret)
    monkeypatch.setattr("app.core.auth.get_settings", lambda: settings)
    assert client.get("/api/validations").status_code == 401

    token = jwt.encode({"sub": "student-1", "aud": "authenticated"}, secret, algorithm="HS256")
    response = client.get("/api/validations", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
