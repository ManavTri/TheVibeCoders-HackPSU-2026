from datetime import date
from decimal import Decimal

from app.schemas.documents import DocumentType, FinancialDocument
from app.services.validation.evaluate import evaluate_findings
from app.services.validation.ledger import build_ledger

TODAY = date(2026, 10, 25)


def document(
    document_id: str,
    document_type: DocumentType,
    term: str | None,
    envelope: dict,
) -> FinancialDocument:
    return FinancialDocument(
        id=document_id,
        filename=f"{document_id}.pdf",
        document_type=document_type,
        currency="USD",
        term=term,
        amount=envelope.get("total_amount"),
        required_credits=envelope.get("required_credits"),
        extraction_envelope=envelope,
        type_confidence=0.98,
    )


def test_multi_term_housing_contract_compares_item_terms_and_skips_equal_fall() -> None:
    contract = document(
        "contract",
        DocumentType.HOUSING_CONTRACT,
        "unrecognized annual period",
        {
            "line_items": [
                {
                    "label": "Fall rate",
                    "amount": "3100",
                    "category": "housing",
                    "kind": "housing",
                    "direction": "charge",
                    "term": "FA26",
                },
                {
                    "label": "Spring rate",
                    "amount": "3300",
                    "category": "housing",
                    "kind": "housing",
                    "direction": "charge",
                    "term": "SP27",
                },
            ],
            "deadlines": [{"label": "Cancellation", "date": "2026-12-01"}],
        },
    )
    bill = document(
        "bill",
        DocumentType.TUITION_BILL,
        "Spring Semester 2027",
        {
            "line_items": [
                {
                    "label": "Spring housing",
                    "amount": "3100",
                    "category": "housing",
                    "kind": "housing",
                    "direction": "charge",
                    "term": "Spring 2027",
                },
                {
                    "label": "Fall housing",
                    "amount": "3100",
                    "category": "housing",
                    "kind": "housing",
                    "direction": "charge",
                    "term": "Fall 2026",
                },
            ],
            "deadlines": [{"label": "Payment due", "date": "2027-01-15"}],
        },
    )

    findings = evaluate_findings([contract, bill], today=TODAY, include_all=True)

    housing = [finding for finding in findings if finding.rule_id == "housing.contract_vs_bill"]
    assert len(housing) == 1
    assert housing[0].term == "Spring 2027"
    assert housing[0].impact_amount == Decimal("200.00")
    assert not any(
        finding.rule_id == "quality.data_gaps" and "contract.pdf" in finding.title
        for finding in findings
    )


def test_past_payment_due_is_suppressed_when_billed_balance_is_zero() -> None:
    bill = document(
        "paid-bill",
        DocumentType.TUITION_BILL,
        "Fall 2026",
        {
            "line_items": [
                {
                    "label": "Tuition",
                    "amount": "1000",
                    "category": "tuition",
                    "kind": "tuition",
                    "direction": "charge",
                    "term": "Fall 2026",
                },
                {
                    "label": "Payment received",
                    "amount": "1000",
                    "category": "payment",
                    "kind": "payment",
                    "direction": "credit",
                    "term": "Fall 2026",
                },
            ],
            "payment_due_dates": [
                {"label": "Payment due", "date": "2026-09-15", "term": "Fall 2026"}
            ],
        },
    )

    findings = evaluate_findings([bill], today=TODAY, include_all=True)

    assert build_ledger([bill], today=TODAY).terms["Fall 2026"]["USD"].net_balance == 0
    assert not any(finding.rule_id == "timing.deadline_status" for finding in findings)


def test_program_double_charge_impact_uses_tuition_only_but_keeps_fee_evidence() -> None:
    quote = document(
        "program",
        DocumentType.STUDY_ABROAD_QUOTE,
        "Spring 2027",
        {
            "line_items": [
                {
                    "label": "Provider tuition",
                    "amount": "8400",
                    "category": "tuition",
                    "kind": "tuition",
                    "direction": "charge",
                    "term": "Spring 2027",
                },
                {
                    "label": "Program and Insurance Fee",
                    "amount": "950",
                    "category": "fee",
                    "kind": "program_fee",
                    "direction": "charge",
                    "term": "Spring 2027",
                },
            ]
        },
    )
    bill = document(
        "home-bill",
        DocumentType.TUITION_BILL,
        "Spring 2027",
        {
            "line_items": [
                {
                    "label": "Home tuition",
                    "amount": "6750",
                    "category": "tuition",
                    "kind": "tuition",
                    "direction": "charge",
                    "term": "Spring 2027",
                }
            ]
        },
    )

    findings = evaluate_findings([quote, bill], today=TODAY, include_all=True)

    double_charge = next(
        finding for finding in findings if finding.rule_id == "program.double_charge"
    )
    assert double_charge.impact_amount == Decimal("6750.00")
    assert any(evidence.label == "Program and Insurance Fee" for evidence in double_charge.evidence)
    assert "8,400.00" in double_charge.explanation
    assert "6,750.00" in double_charge.explanation
