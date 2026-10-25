import importlib
import json
import pkgutil
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from app.db.repositories import _finding_from_row
from app.schemas.documents import ExtractionEnvelope, FinancialDocument
from app.schemas.validation import Severity
from app.services.validation import engine
from app.services.validation.evaluate import evaluate_findings
from app.services.validation.rules import base as rule_base

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "term_ledger_scenarios.json"
TODAY = date(2026, 7, 1)


def _document(data: dict) -> FinancialDocument:
    return FinancialDocument.model_validate(data)


@pytest.mark.parametrize(
    "scenario",
    json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))["scenarios"],
    ids=lambda scenario: scenario["name"],
)
def test_fixture_scenario_produces_specific_evidence_backed_findings(scenario: dict) -> None:
    documents = [_document(item) for item in scenario["documents"]]
    findings = evaluate_findings(documents, today=TODAY, include_all=True)
    expected = scenario["expected"]
    expected_findings = expected if isinstance(expected, list) else [expected]
    for item in expected_findings:
        finding = next(
            (
                candidate
                for candidate in findings
                if candidate.rule_id == item["rule_id"]
                and candidate.term == item["term"]
            ),
            None,
        )
        assert finding is not None, scenario["name"]
        assert finding.severity.value == item["severity"]
        assert finding.impact_amount == (
            Decimal(item["impact_amount"]) if item["impact_amount"] is not None else None
        )
        assert finding.evidence
        assert finding.suggested_action.strip()
        assert finding.title.strip()
        assert finding.title.casefold() not in {"dates differ", "terms differ", "dates conflict"}


def test_different_terms_are_allocation_data_not_findings() -> None:
    documents = [
        _document(
            {
                "id": "award",
                "filename": "award.pdf",
                "document_type": "award_letter",
                "amount": "1000",
                "term": "Fall 2026",
            }
        ),
        _document(
            {
                "id": "bill",
                "filename": "bill.pdf",
                "document_type": "tuition_bill",
                "amount": "1500",
                "term": "Spring 2027",
            }
        ),
    ]

    findings = evaluate_findings(documents, today=TODAY, include_all=True)

    assert not {
        finding.rule_id
        for finding in findings
    }.intersection({"term.documents_disagree", "deadline.different_dates"})


def test_unknown_terms_create_one_quality_finding_per_document_without_term_noise() -> None:
    documents = [
        _document(
            {
                "id": f"unknown-{index}",
                "filename": f"unknown-{index}.pdf",
                "document_type": "other",
                "term": "quarterly term",
                "type_confidence": 0.4,
            }
        )
        for index in range(3)
    ]

    findings = evaluate_findings(documents, today=TODAY, include_all=True)

    quality = [finding for finding in findings if finding.rule_id == "quality.data_gaps"]
    assert len(quality) == 3
    assert {finding.document_ids[0] for finding in quality} == {
        "unknown-0",
        "unknown-1",
        "unknown-2",
    }
    assert not any(finding.rule_id.startswith(("term.", "timing.")) for finding in findings)


def test_default_response_caps_info_findings_to_three() -> None:
    documents = [
        _document(
            {
                "id": f"condition-{index}",
                "filename": f"condition-{index}.pdf",
                "document_type": "award_letter",
                "term": f"Fall {2026 + index}",
                "extraction_envelope": {"conditions": [f"Maintain condition {index}"]},
            }
        )
        for index in range(6)
    ]

    default = evaluate_findings(documents, today=TODAY)
    all_findings = evaluate_findings(documents, today=TODAY, include_all=True)

    assert sum(finding.severity is Severity.INFO for finding in default) <= 3
    assert len(all_findings) > len(default)


def test_same_input_has_stable_order_and_ids() -> None:
    scenario = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))["scenarios"][4]
    documents = [_document(item) for item in scenario["documents"]]

    first = evaluate_findings(documents, today=TODAY, include_all=True)
    second = evaluate_findings(documents, today=TODAY, include_all=True)

    assert [(finding.id, finding.rule_id) for finding in first] == [
        (finding.id, finding.rule_id) for finding in second
    ]


def test_strict_validation_reraises_rule_exception(monkeypatch) -> None:
    scenario = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))["scenarios"][0]
    documents = [_document(item) for item in scenario["documents"]]

    def failing_rule(_context):
        raise RuntimeError("fixture error")

    original = engine.RULES
    monkeypatch.setattr(
        engine,
        "RULES",
        (engine.RuleDefinition("test.failing_rule", failing_rule), *original),
    )

    with pytest.raises(RuntimeError, match="fixture error"):
        evaluate_findings(
            documents,
            today=TODAY,
            include_all=True,
            config=rule_base.ValidationConfig(strict=True),
        )


def test_non_strict_validation_records_rule_errors_and_continues(monkeypatch, caplog) -> None:
    scenario = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))["scenarios"][0]
    documents = [_document(item) for item in scenario["documents"]]

    def failing_rule(_context):
        raise RuntimeError("document content must not appear in logs")

    original = engine.RULES
    monkeypatch.setattr(
        engine,
        "RULES",
        (engine.RuleDefinition("test.failing_rule", failing_rule), *original),
    )
    errors: list[dict[str, str]] = []

    findings = evaluate_findings(
        documents,
        today=TODAY,
        include_all=True,
        config=rule_base.ValidationConfig(strict=False),
        rule_errors=errors,
    )

    assert errors == [{"rule_id": "test.failing_rule", "error_class": "RuntimeError"}]
    assert any(finding.rule_id == "coverage.term_gap" for finding in findings)
    assert "ERROR" in caplog.text
    assert "test.failing_rule" in caplog.text
    assert "RuntimeError" in caplog.text
    assert "document content must not appear in logs" not in caplog.text


def test_all_validation_rule_modules_and_registered_rules_run_strictly() -> None:
    rules_package = importlib.import_module("app.services.validation.rules")
    for module in pkgutil.iter_modules(
        rules_package.__path__, f"{rules_package.__name__}."
    ):
        importlib.import_module(module.name)

    scenario_dir = (
        Path(__file__).resolve().parents[2]
        / "sample_docs"
        / "scenario_3_two_term_demo"
        / "envelopes"
    )
    documents = []
    for envelope_path in sorted(scenario_dir.glob("*.json")):
        envelope = json.loads(envelope_path.read_text(encoding="utf-8"))
        parsed = ExtractionEnvelope.model_validate(envelope)
        documents.append(
            FinancialDocument(
                id=envelope_path.stem,
                filename=f"{envelope_path.stem}.pdf",
                document_type=parsed.document_type,
                amount=parsed.total_amount,
                currency=parsed.currency or "USD",
                term=parsed.term,
                deadline=min((item.date for item in parsed.deadlines), default=None),
                required_credits=parsed.required_credits,
                extraction_envelope=parsed.model_dump(mode="json"),
            )
        )

    assert len(documents) == 6
    evaluate_findings(
        documents,
        today=date(2026, 10, 25),
        include_all=True,
        config=rule_base.ValidationConfig(strict=True),
    )


def test_legacy_saved_finding_without_details_still_loads() -> None:
    finding = _finding_from_row(
        {
            "rule_id": "legacy.rule",
            "severity": "warning",
            "title": "Legacy finding",
            "explanation": "Legacy explanation.",
            "document_ids": ["legacy-doc"],
            "fields": {"amount": "1.00"},
            "suggested_action": "Check the original notice.",
            "details": None,
        }
    )

    assert finding.rule_id == "legacy.rule"
    assert finding.category is None
    assert finding.evidence == []
    assert finding.id


def test_saved_finding_details_round_trip_additive_fields() -> None:
    finding = _finding_from_row(
        {
            "rule_id": "coverage.term_gap",
            "severity": "warning",
            "title": "Fall 2026 gap",
            "explanation": "A gap remains.",
            "document_ids": ["bill"],
            "fields": {},
            "suggested_action": "Ask billing.",
            "details": {
                "id": "stable-finding-id",
                "category": "coverage",
                "term": "Fall 2026",
                "impact_amount": "100.00",
                "confidence": "high",
                "evidence": [
                    {
                        "document_id": "bill",
                        "filename": "bill.pdf",
                        "field": "amount",
                        "label": "Tuition",
                        "value": "100.00",
                    }
                ],
                "group_key": "fall-gap",
            },
        }
    )

    assert finding.id == "stable-finding-id"
    assert finding.term == "Fall 2026"
    assert finding.evidence[0].label == "Tuition"
