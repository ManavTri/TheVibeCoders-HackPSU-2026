from pathlib import Path
from uuid import uuid4

import jwt
from app.core.auth import current_user
from app.core.config import Settings
from app.main import app
from fastapi.testclient import TestClient

SAMPLES = Path(__file__).resolve().parents[2] / "sample_docs" / "scenario_1_mismatch"


def upload_pair(client: TestClient) -> list[dict]:
    award = (SAMPLES / "award_letter.pdf").read_bytes()
    bill = (SAMPLES / "tuition_bill.pdf").read_bytes()
    responses = [
        client.post(
            "/api/documents",
            files={"file": ("award_letter.pdf", award, "application/pdf")},
            data={"document_type": "award_letter"},
        ),
        client.post(
            "/api/documents",
            files={"file": ("tuition_bill.pdf", bill, "application/pdf")},
            data={"document_type": "tuition_bill"},
        ),
    ]
    assert all(response.status_code == 201 for response in responses)
    return [response.json() for response in responses]


def test_health(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_documents_validations_and_insights_flow(client: TestClient) -> None:
    documents = upload_pair(client)
    assert all(document["status"] == "extracted" for document in documents)
    listed = client.get("/api/documents")
    assert listed.status_code == 200
    assert len(listed.json()) == 2
    detail = client.get(f"/api/documents/{documents[0]['id']}")
    assert detail.status_code == 200
    assert "user_id" not in detail.json()
    assert "storage_path" not in detail.json()

    created = client.post("/api/validations", json={"document_ids": [doc["id"] for doc in documents]})
    assert created.status_code == 201
    report = created.json()
    assert {finding["rule_id"] for finding in report["findings"]} == {
        "deadline.different_dates",
        "term.documents_disagree",
        "credits.requirements_disagree",
    }
    assert client.get(f"/api/validations/{report['id']}").status_code == 200
    insights = client.post("/api/insights", json={"run_id": report["id"]}).json()
    assert insights["report_id"] == report["id"]
    assert insights["recommendations"]


def test_patch_correction_is_saved_and_validation_can_be_rerun(client: TestClient) -> None:
    documents = upload_pair(client)
    award = documents[0]
    corrected = client.patch(
        f"/api/documents/{award['id']}",
        json={"term": "Spring 2026", "required_credits": 6},
    )
    assert corrected.status_code == 200
    assert corrected.json()["term"] == "Spring 2026"
    assert corrected.json()["required_credits"] == 6

    report = client.post(
        "/api/validations",
        json={"document_ids": [document["id"] for document in documents]},
    )
    assert report.status_code == 201
    assert "term.documents_disagree" not in {finding["rule_id"] for finding in report.json()["findings"]}
    assert "credits.requirements_disagree" not in {finding["rule_id"] for finding in report.json()["findings"]}


def test_delete_removes_document_and_file(client: TestClient) -> None:
    documents = upload_pair(client)
    report = client.post(
        "/api/validations",
        json={"document_ids": [item["id"] for item in documents]},
    ).json()
    document = documents[0]
    assert client.get(f"/api/documents/{document['id']}/file").status_code == 200
    assert client.delete(f"/api/documents/{document['id']}").status_code == 204
    assert client.get(f"/api/documents/{document['id']}").status_code == 404
    assert client.get(f"/api/documents/{document['id']}/file").status_code == 404
    assert client.get(f"/api/validations/{report['id']}").status_code == 404


def test_validation_requires_two_extracted_documents(client: TestClient) -> None:
    assert client.post("/api/validations", json={"document_ids": []}).status_code == 400


def test_validation_without_body_uses_all_user_documents(client: TestClient) -> None:
    upload_pair(client)
    response = client.post("/api/validations")
    assert response.status_code == 201
    assert len(response.json()["documents"]) == 2


def test_missing_resources_return_404(client: TestClient) -> None:
    missing_id = str(uuid4())
    assert client.get(f"/api/documents/{missing_id}").status_code == 404
    assert client.patch(f"/api/documents/{missing_id}", json={"term": "Fall 2026"}).status_code == 404
    assert client.delete(f"/api/documents/{missing_id}").status_code == 404
    assert client.get(f"/api/validations/{missing_id}").status_code == 404
    assert client.post("/api/insights", json={"run_id": missing_id}).status_code == 404


def test_supabase_hs256_authentication_is_enforced(client: TestClient, monkeypatch) -> None:
    secret = "test-secret-for-hs256-key-long-enough"
    settings = Settings(require_auth=True, supabase_jwt_secret=secret)
    monkeypatch.setattr("app.core.auth.get_settings", lambda: settings)
    assert client.get("/api/documents").status_code == 401

    token = jwt.encode({"sub": "f266b450-a4db-4a58-9d55-9ed4e5e4c0e8", "aud": "authenticated"}, secret, algorithm="HS256")
    response = client.get("/api/documents", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    invalid_subject = jwt.encode({"sub": "not-a-uuid", "aud": "authenticated"}, secret, algorithm="HS256")
    assert client.get("/api/documents", headers={"Authorization": f"Bearer {invalid_subject}"}).status_code == 401


def test_supabase_configuration_never_uses_anonymous_local_identity(client: TestClient, monkeypatch) -> None:
    settings = Settings(
        require_auth=False,
        supabase_url="https://example.supabase.co",
        supabase_service_key="test-service-key",
    )
    monkeypatch.setattr("app.core.auth.get_settings", lambda: settings)
    assert client.get("/api/documents").status_code == 401


def test_validation_reports_are_isolated_between_users(client: TestClient) -> None:
    first_user_documents = upload_pair(client)
    report = client.post(
        "/api/validations",
        json={"document_ids": [document["id"] for document in first_user_documents]},
    ).json()

    app.dependency_overrides[current_user] = lambda: {"sub": "a266b450-a4db-4a58-9d55-9ed4e5e4c0e8"}
    assert client.get(f"/api/validations/{report['id']}").status_code == 404
    assert client.get(f"/api/documents/{first_user_documents[0]['id']}").status_code == 404
