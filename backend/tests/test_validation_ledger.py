from datetime import date
from decimal import Decimal

from app.schemas.documents import DocumentType, FinancialDocument
from app.services.validation.ledger import build_ledger


def make_document(
    document_id: str,
    document_type: DocumentType,
    *,
    amount: str | None = None,
    term: str | None = None,
    currency: str = "USD",
    envelope: dict | None = None,
) -> FinancialDocument:
    return FinancialDocument(
        id=document_id,
        filename=f"{document_id}.pdf",
        document_type=document_type,
        amount=Decimal(amount) if amount else None,
        term=term,
        currency=currency,
        extraction_envelope=envelope,
    )


def test_multi_term_award_and_two_bills_have_per_term_and_overall_balances() -> None:
    award = make_document(
        "award",
        DocumentType.AWARD_LETTER,
        term="Academic Year 2026-2027",
        envelope={
            "terms": ["Academic Year 2026-2027"],
            "line_items": [
                {
                    "label": "Hope Scholarship Fall",
                    "amount": "4000",
                    "category": "scholarship",
                    "kind": "scholarship",
                    "direction": "credit",
                    "term": "Fall 2026",
                },
                {
                    "label": "Hope Scholarship Spring",
                    "amount": "3000",
                    "category": "scholarship",
                    "kind": "scholarship",
                    "direction": "credit",
                    "term": "Spring 2027",
                },
            ],
        },
    )
    fall_bill = make_document(
        "fall-bill",
        DocumentType.TUITION_BILL,
        term="Fall 2026",
        envelope={
            "line_items": [
                {
                    "label": "Tuition",
                    "amount": "6000",
                    "category": "tuition",
                    "kind": "tuition",
                    "direction": "charge",
                }
            ]
        },
    )
    spring_bill = make_document(
        "spring-bill",
        DocumentType.TUITION_BILL,
        term="Spring 2027",
        envelope={
            "line_items": [
                {
                    "label": "Tuition",
                    "amount": "5000",
                    "category": "tuition",
                    "kind": "tuition",
                    "direction": "charge",
                }
            ]
        },
    )

    ledger = build_ledger([award, fall_bill, spring_bill], today=date(2026, 7, 1))

    assert ledger.terms["Fall 2026"]["USD"].charges == Decimal(6000)
    assert ledger.terms["Fall 2026"]["USD"].aid == Decimal(4000)
    assert ledger.terms["Fall 2026"]["USD"].gap == Decimal(2000)
    assert ledger.terms["Spring 2027"]["USD"].charges == Decimal(5000)
    assert ledger.terms["Spring 2027"]["USD"].aid == Decimal(3000)
    assert ledger.terms["Spring 2027"]["USD"].net_balance == Decimal("2000.00")
    assert ledger.total["USD"].charges == Decimal(11000)
    assert ledger.total["USD"].aid == Decimal(7000)
    assert len(ledger.terms["Fall 2026"]["USD"].entries) == 2


def test_academic_year_disbursements_are_allocated_by_explicit_term() -> None:
    award = make_document(
        "annual-award",
        DocumentType.AWARD_LETTER,
        amount="9000",
        term="Academic Year 2026-2027",
        envelope={
            "academic_year": "2026-2027",
            "disbursements": [
                {"date": "2026-08-20", "amount": "5000", "term": "Fall 2026"},
                {"date": "2027-01-15", "amount": "4000", "term": "Spring 2027"},
            ],
        },
    )

    ledger = build_ledger([award], today=date(2026, 7, 1))

    assert ledger.terms["Fall 2026"]["USD"].expected_disbursements[0].amount == Decimal(
        "5000.00"
    )
    assert ledger.terms["Spring 2027"]["USD"].expected_disbursements[0].date == "2027-01-15"
    assert ledger.annual_unallocated["2026-2027"]["USD"].aid == Decimal("9000.00")
    assert ledger.total["USD"].aid == Decimal("9000.00")
    assert len(ledger.total["USD"].expected_disbursements) == 2


def test_multi_term_item_without_its_own_term_is_annual_unallocated() -> None:
    document = make_document(
        "annual",
        DocumentType.AWARD_LETTER,
        term="Academic Year 2026-2027",
        envelope={
            "line_items": [
                {
                    "label": "Annual grant",
                    "amount": "1200",
                    "category": "grant",
                    "kind": "grant",
                    "direction": "credit",
                }
            ]
        },
    )

    ledger = build_ledger([document], today=date(2026, 7, 1))

    assert ledger.annual_unallocated["2026-2027"]["USD"].aid == Decimal("1200.00")
    assert ledger.terms == {}
    assert ledger.total["USD"].aid == Decimal("1200.00")


def test_program_estimates_are_separate_from_billed_charges() -> None:
    quote = make_document(
        "abroad",
        DocumentType.STUDY_ABROAD_QUOTE,
        amount="8500",
        term="Fall 2026",
        envelope={
            "line_items": [
                {
                    "label": "Program tuition estimate",
                    "amount": "8500",
                    "category": "tuition",
                    "kind": "tuition",
                    "direction": "charge",
                }
            ]
        },
    )

    ledger = build_ledger([quote], today=date(2026, 7, 1))

    assert ledger.estimates[0].amount == Decimal("8500.00")
    assert ledger.total == {}
    assert ledger.terms == {}


def test_currency_totals_are_kept_separate_for_a_term() -> None:
    usd_bill = make_document(
        "usd",
        DocumentType.TUITION_BILL,
        currency="USD",
        term="Fall 2026",
        envelope={
            "line_items": [
                {
                    "label": "Tuition",
                    "amount": "1000",
                    "category": "tuition",
                    "kind": "tuition",
                    "direction": "charge",
                }
            ]
        },
    )
    eur_bill = make_document(
        "eur",
        DocumentType.TUITION_BILL,
        currency="EUR",
        term="Fall 2026",
        envelope={
            "currency": "EUR",
            "line_items": [
                {
                    "label": "Program fee",
                    "amount": "200",
                    "category": "fee",
                    "kind": "fees",
                    "direction": "charge",
                }
            ],
        },
    )

    ledger = build_ledger([usd_bill, eur_bill], today=date(2026, 7, 1))

    assert set(ledger.terms["Fall 2026"]) == {"USD", "EUR"}
    assert ledger.terms["Fall 2026"]["USD"].charges == Decimal("1000.00")
    assert ledger.terms["Fall 2026"]["EUR"].charges == Decimal("200.00")
    assert set(ledger.total) == {"USD", "EUR"}
