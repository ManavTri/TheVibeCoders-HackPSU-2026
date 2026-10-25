import json
from decimal import Decimal
from pathlib import Path

from app.schemas.documents import DocumentType, FinancialDocument
from app.services.extraction.extractor import extract_document
from app.services.validation.engine import validate_documents
from app.services.validation.evaluate import evaluate_findings

FIXTURES = Path(__file__).parent / "fixtures"


def fixture_document(filename: str) -> FinancialDocument:
    return FinancialDocument.model_validate_json((FIXTURES / filename).read_text(encoding="utf-8"))


def test_scenario_finds_expected_conflicts() -> None:
    documents = [fixture_document("award_letter.json"), fixture_document("tuition_bill.json")]
    findings = validate_documents(documents)
    expected = {
        "coverage.term_gap",
        "eligibility.credit_requirement",
    }
    assert expected.issubset({finding.rule_id for finding in findings})
    assert "coverage.term_surplus" not in {finding.rule_id for finding in findings}
    assert not {
        "deadline.different_dates",
        "term.documents_disagree",
        "credits.requirements_disagree",
    }.intersection({finding.rule_id for finding in findings})


def test_unbilled_award_does_not_create_a_billed_surplus() -> None:
    award = fixture_document("award_letter.json")
    bill = fixture_document("tuition_bill.json").model_copy(update={"amount": 10000})
    findings = validate_documents([award, bill])
    assert "coverage.term_surplus" not in {finding.rule_id for finding in findings}
    assert "coverage.term_gap" in {finding.rule_id for finding in findings}


def test_extractor_reads_explicit_fields() -> None:
    extracted = extract_document(
        document_id="doc-1",
        filename="award.pdf",
        document_type=DocumentType.AWARD_LETTER,
        text="Scholarship award amount: $4,250.00\nFall 2026 term\nPayment due: July 15, 2026\nMinimum 12 credits",
    )
    assert str(extracted.amount) == "4250.00"
    assert extracted.term == "Fall 2026"
    assert extracted.deadline.isoformat() == "2026-07-15"
    assert extracted.required_credits == 12


def test_non_conflicting_amounts_do_not_trigger_award_rule() -> None:
    award = fixture_document("award_letter.json").model_copy(update={"amount": 1000})
    bill = fixture_document("tuition_bill.json").model_copy(update={"amount": 18000})
    findings = validate_documents([award, bill])
    assert "award.amount_mismatch" not in {finding.rule_id for finding in findings}


def test_fixture_files_are_valid_json() -> None:
    for path in FIXTURES.glob("*.json"):
        json.loads(path.read_text(encoding="utf-8"))


def test_finding_ids_are_stable_and_track_the_document_set() -> None:
    award = fixture_document("award_letter.json")
    bill = fixture_document("tuition_bill.json")
    initial = evaluate_findings([award, bill])
    repeated = evaluate_findings([award, bill])
    assert [finding.id for finding in initial] == [finding.id for finding in repeated]

    second_bill = bill.model_copy(update={"id": "second-bill", "amount": Decimal(500)})
    expanded = evaluate_findings([award, bill, second_bill])
    original_gap = next(
        finding for finding in initial if finding.rule_id == "coverage.term_gap"
    )
    expanded_gap = next(
        finding for finding in expanded if finding.rule_id == "coverage.term_gap"
    )
    assert original_gap.id != expanded_gap.id
