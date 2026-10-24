import json
from io import BytesIO
from pathlib import Path

from pypdf import PdfWriter

SAMPLES = Path(__file__).resolve().parents[2] / "sample_docs"


def test_extract_endpoint_rejects_non_pdf(client) -> None:
    response = client.post(
        "/api/documents/extract",
        files=[("files", ("statement.txt", b"not pdf", "text/plain"))],
        data={"document_types": "award_letter"},
    )
    assert response.status_code == 415


def test_extract_endpoint_rejects_pdf_without_text(client) -> None:
    writer = PdfWriter()
    writer.add_blank_page(width=300, height=300)
    output = BytesIO()
    writer.write(output)
    response = client.post(
        "/api/documents/extract",
        files=[("files", ("blank.pdf", output.getvalue(), "application/pdf"))],
        data={"document_types": "award_letter"},
    )
    assert response.status_code == 422


def test_extract_endpoint_reads_synthetic_sample_pdfs(client) -> None:
    award = (SAMPLES / "scenario_1_mismatch" / "award_letter.pdf").read_bytes()
    bill = (SAMPLES / "scenario_1_mismatch" / "tuition_bill.pdf").read_bytes()
    response = client.post(
        "/api/documents/extract",
        files=[
            ("files", ("award_letter.pdf", award, "application/pdf")),
            ("files", ("tuition_bill.pdf", bill, "application/pdf")),
        ],
        data={"document_types": ["award_letter", "tuition_bill"]},
    )
    assert response.status_code == 200
    documents = response.json()
    assert float(documents[0]["amount"]) == 12000
    assert documents[0]["term"] == "Fall 2026"
    assert float(documents[1]["amount"]) == 18000
    assert documents[1]["term"] == "Spring 2026"
    assert "extracted_text" not in documents[0]
    report = client.post("/api/validations", json=documents)
    assert report.status_code == 201
    expected = json.loads((SAMPLES / "scenario_1_mismatch" / "expected.json").read_text(encoding="utf-8"))
    assert {finding["rule_id"] for finding in report.json()["findings"]} == set(expected["expected_rule_ids"])


def test_study_abroad_sample_matches_expected_rules(client) -> None:
    scenario = SAMPLES / "scenario_2_study_abroad"
    response = client.post(
        "/api/documents/extract",
        files=[
            ("files", ("award_letter.pdf", (scenario / "award_letter.pdf").read_bytes(), "application/pdf")),
            ("files", ("study_abroad_quote.pdf", (scenario / "study_abroad_quote.pdf").read_bytes(), "application/pdf")),
        ],
        data={"document_types": ["award_letter", "study_abroad_quote"]},
    )
    assert response.status_code == 200
    report = client.post("/api/validations", json=response.json())
    assert report.status_code == 201
    expected = json.loads((scenario / "expected.json").read_text(encoding="utf-8"))
    assert {finding["rule_id"] for finding in report.json()["findings"]} == set(expected["expected_rule_ids"])
