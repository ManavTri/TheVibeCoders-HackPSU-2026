import json
from io import BytesIO
from pathlib import Path

from fastapi.testclient import TestClient
from pypdf import PdfWriter

SAMPLES = Path(__file__).resolve().parents[2] / "sample_docs"


def upload(client: TestClient, path: Path, document_type: str) -> dict:
    response = client.post(
        "/api/documents",
        files={"file": (path.name, path.read_bytes(), "application/pdf")},
        data={"document_type": document_type},
    )
    assert response.status_code == 201
    return response.json()


def test_document_endpoint_rejects_non_pdf(client: TestClient) -> None:
    response = client.post(
        "/api/documents",
        files={"file": ("statement.txt", b"not pdf", "text/plain")},
        data={"document_type": "award_letter"},
    )
    assert response.status_code == 415


def test_document_endpoint_marks_pdf_without_text_failed(client: TestClient) -> None:
    writer = PdfWriter()
    writer.add_blank_page(width=300, height=300)
    output = BytesIO()
    writer.write(output)
    response = client.post(
        "/api/documents",
        files={"file": ("blank.pdf", output.getvalue(), "application/pdf")},
        data={"document_type": "award_letter"},
    )
    assert response.status_code == 201
    assert response.json()["status"] == "failed"
    assert "no selectable text" in response.json()["extraction_error"]


def test_scenario_one_pdfs_match_expected_rules(client: TestClient) -> None:
    scenario = SAMPLES / "scenario_1_mismatch"
    documents = [
        upload(client, scenario / "award_letter.pdf", "award_letter"),
        upload(client, scenario / "tuition_bill.pdf", "tuition_bill"),
    ]
    assert float(documents[0]["amount"]) == 12000
    assert documents[0]["term"] == "Fall 2026"
    assert float(documents[1]["amount"]) == 18000
    assert documents[1]["term"] == "Spring 2026"
    assert "extracted_text" not in documents[0]
    report = client.get("/api/findings?include=all")
    assert report.status_code == 200
    expected = json.loads((scenario / "expected.json").read_text(encoding="utf-8"))
    actual = {finding["rule_id"] for finding in report.json()}
    assert set(expected["expected_rule_ids"]).issubset(actual)
    assert "coverage.term_surplus" not in actual
    assert not set(expected.get("expected_absent_rule_ids", [])).intersection(actual)


def test_study_abroad_sample_matches_expected_rules(client: TestClient) -> None:
    scenario = SAMPLES / "scenario_2_study_abroad"
    upload(client, scenario / "award_letter.pdf", "award_letter")
    upload(client, scenario / "study_abroad_quote.pdf", "study_abroad_quote")
    report = client.get("/api/findings?include=all")
    assert report.status_code == 200
    expected = json.loads((scenario / "expected.json").read_text(encoding="utf-8"))
    actual = {finding["rule_id"] for finding in report.json()}
    assert set(expected["expected_rule_ids"]).issubset(actual)
    assert "coverage.term_surplus" not in actual
    assert not set(expected.get("expected_absent_rule_ids", [])).intersection(actual)
