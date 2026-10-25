from pathlib import Path
from uuid import uuid4

import jwt
from fastapi.testclient import TestClient

from app.core.auth import current_user
from app.core.config import Settings
from app.main import app

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


def test_duplicate_upload_returns_existing_document(client: TestClient) -> None:
    content = (SAMPLES / "award_letter.pdf").read_bytes()
    upload = {
        "files": {"file": ("award.pdf", content, "application/pdf")},
        "data": {"document_type": "award_letter"},
    }
    first = client.post("/api/documents", **upload)
    duplicate = client.post("/api/documents", **upload)

    assert first.status_code == 201
    assert duplicate.status_code == 409
    detail = duplicate.json()["detail"]
    assert detail["code"] == "duplicate_document"
    assert detail["existing"]["id"] == first.json()["id"]
    assert detail["existing"]["state"] == "active"
    assert "already uploaded" in detail["message"]


def test_same_filename_with_different_content_is_allowed(client: TestClient) -> None:
    award = (SAMPLES / "award_letter.pdf").read_bytes()
    bill = (SAMPLES / "tuition_bill.pdf").read_bytes()
    first = client.post(
        "/api/documents",
        files={"file": ("statement.pdf", award, "application/pdf")},
        data={"document_type": "award_letter"},
    )
    second = client.post(
        "/api/documents",
        files={"file": ("statement.pdf", bill, "application/pdf")},
        data={"document_type": "tuition_bill"},
    )

    assert first.status_code == second.status_code == 201
    assert first.json()["filename"] == second.json()["filename"]
    assert first.json()["id"] != second.json()["id"]


def test_duplicate_of_archived_document_returns_archived_state(client: TestClient) -> None:
    content = (SAMPLES / "award_letter.pdf").read_bytes()
    upload = {
        "files": {"file": ("award.pdf", content, "application/pdf")},
        "data": {"document_type": "award_letter"},
    }
    original = client.post("/api/documents", **upload).json()
    archived = client.post(f"/api/documents/{original['id']}/archive")
    duplicate = client.post("/api/documents", **upload)

    assert archived.status_code == 200
    assert archived.json()["state"] == "archived"
    assert duplicate.status_code == 409
    assert duplicate.json()["detail"]["existing"]["id"] == original["id"]
    assert duplicate.json()["detail"]["existing"]["state"] == "archived"


def test_identical_bytes_can_be_uploaded_by_different_users(client: TestClient) -> None:
    content = (SAMPLES / "award_letter.pdf").read_bytes()
    request = {
        "files": {"file": ("award.pdf", content, "application/pdf")},
        "data": {"document_type": "award_letter"},
    }
    first = client.post("/api/documents", **request)

    app.dependency_overrides[current_user] = lambda: {"sub": "a266b450-a4db-4a58-9d55-9ed4e5e4c0e8"}
    second = client.post("/api/documents", **request)

    assert first.status_code == second.status_code == 201
    assert first.json()["id"] != second.json()["id"]


def test_archive_restore_soft_delete_and_state_filter(client: TestClient) -> None:
    documents = upload_pair(client)
    document_id = documents[0]["id"]

    archived = client.post(f"/api/documents/{document_id}/archive")
    assert archived.status_code == 200
    assert archived.json()["state"] == "archived"
    assert archived.json()["archived_at"] is not None
    assert [doc["id"] for doc in client.get("/api/documents?state=archived").json()] == [document_id]
    assert document_id not in {doc["id"] for doc in client.get("/api/documents").json()}

    restored = client.post(f"/api/documents/{document_id}/restore")
    assert restored.status_code == 200
    assert restored.json()["state"] == "active"
    assert restored.json()["archived_at"] is None

    deleted = client.post(f"/api/documents/{document_id}/delete")
    assert deleted.status_code == 200
    assert deleted.json()["state"] == "deleted"
    assert deleted.json()["deleted_at"] is not None
    assert [doc["id"] for doc in client.get("/api/documents?state=deleted").json()] == [document_id]
    assert document_id not in {doc["id"] for doc in client.get("/api/documents").json()}
    restored_deleted = client.post(f"/api/documents/{document_id}/restore")
    assert restored_deleted.status_code == 200
    assert restored_deleted.json()["state"] == "active"


def test_current_findings_only_include_active_extracted_documents(client: TestClient) -> None:
    scenario_2 = Path(__file__).resolve().parents[2] / "sample_docs" / "scenario_2_study_abroad"
    documents = [
        client.post(
            "/api/documents",
            files={"file": (path.name, path.read_bytes(), "application/pdf")},
            data={"document_type": document_type},
        ).json()
        for path, document_type in (
            (SAMPLES / "award_letter.pdf", "award_letter"),
            (SAMPLES / "tuition_bill.pdf", "tuition_bill"),
            (scenario_2 / "award_letter.pdf", "award_letter"),
            (scenario_2 / "study_abroad_quote.pdf", "study_abroad_quote"),
        )
    ]
    archived_id, deleted_id = documents[1]["id"], documents[2]["id"]
    assert client.post(f"/api/documents/{archived_id}/archive").status_code == 200
    assert client.post(f"/api/documents/{deleted_id}/delete").status_code == 200

    findings = client.get("/api/findings")
    assert findings.status_code == 200
    assert findings.json()
    referenced_ids = {
        document_id
        for finding in findings.json()
        for document_id in finding["document_ids"]
    }
    assert archived_id not in referenced_ids
    assert deleted_id not in referenced_ids
    assert {finding["id"] for finding in findings.json()} == {
        finding["id"] for finding in client.get("/api/findings").json()
    }


def test_current_findings_are_empty_with_fewer_than_two_active_documents(client: TestClient) -> None:
    award = (SAMPLES / "award_letter.pdf").read_bytes()
    uploaded = client.post(
        "/api/documents",
        files={"file": ("award.pdf", award, "application/pdf")},
        data={"document_type": "award_letter"},
    )
    assert uploaded.status_code == 201
    assert client.get("/api/findings").json() == []


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
