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
    assert ledger.terms["Fall 2026"]["USD"].aid == Decimal(0)
    assert ledger.terms["Fall 2026"]["USD"].expected_not_yet_billed[0].amount == Decimal(
        "4000.00"
    )
    assert ledger.terms["Spring 2027"]["USD"].charges == Decimal(5000)
    assert ledger.terms["Spring 2027"]["USD"].aid == Decimal(0)
    assert ledger.terms["Spring 2027"]["USD"].expected_not_yet_billed[0].amount == Decimal(
        "3000.00"
    )
    assert ledger.total["USD"].charges == Decimal(11000)
    assert ledger.total["USD"].aid == Decimal(0)
    assert len(ledger.terms["Fall 2026"]["USD"].entries) == 1


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
    assert ledger.annual_unallocated["2026-2027"]["USD"].aid == Decimal(0)
    assert ledger.annual_unallocated["2026-2027"]["USD"].expected_not_yet_billed[0].amount == Decimal(
        "9000.00"
    )
    assert ledger.total["USD"].aid == Decimal(0)
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

    assert ledger.annual_unallocated["2026-2027"]["USD"].aid == Decimal(0)
    assert ledger.annual_unallocated["2026-2027"]["USD"].expected_not_yet_billed[0].amount == Decimal(
        "1200.00"
    )
    assert ledger.terms == {}
    assert ledger.total["USD"].aid == Decimal(0)
    assert ledger.total["USD"].expected_not_yet_billed[0].amount == Decimal("1200.00")


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


def test_bill_is_balance_source_and_housing_contract_is_reference_only() -> None:
    bill = make_document(
        "bill",
        DocumentType.TUITION_BILL,
        term="Spring 2027",
        envelope={
            "line_items": [
                {
                    "label": "Residence Hall",
                    "amount": "3100",
                    "category": "housing",
                    "kind": "housing",
                    "direction": "charge",
                    "term": "Spring 2027",
                }
            ]
        },
    )
    contract = make_document(
        "contract",
        DocumentType.HOUSING_CONTRACT,
        term="Multi-term housing agreement",
        envelope={
            "line_items": [
                {
                    "label": "Spring room rate",
                    "amount": "3300",
                    "category": "housing",
                    "kind": "housing",
                    "direction": "charge",
                    "term": "Spring 2027",
                }
            ]
        },
    )

    ledger = build_ledger([bill, contract], today=date(2026, 10, 25))
    spring = ledger.terms["Spring 2027"]["USD"]

    assert spring.charges == Decimal("3100.00")
    assert spring.net_balance == Decimal("3100.00")
    assert spring.committed_not_yet_billed == []
    assert [entry.amount for entry in spring.reference_entries] == [Decimal("3300.00")]


def test_bill_credit_is_counted_once_and_award_difference_is_expected_only() -> None:
    bill = make_document(
        "spring-bill",
        DocumentType.TUITION_BILL,
        term="Spring 2027",
        envelope={
            "line_items": [
                {
                    "label": "Tuition",
                    "amount": "10000",
                    "category": "tuition",
                    "kind": "tuition",
                    "direction": "charge",
                    "term": "Spring 2027",
                },
                {
                    "label": "Alder Ridge Merit Scholarship",
                    "amount": "2500",
                    "category": "scholarship",
                    "kind": "scholarship",
                    "direction": "credit",
                    "term": "Spring 2027",
                },
            ]
        },
    )
    award = make_document(
        "award",
        DocumentType.AWARD_LETTER,
        term="Academic Year 2026-2027",
        envelope={
            "line_items": [
                {
                    "label": "Alder Ridge Merit Scholarship",
                    "amount": "3000",
                    "category": "scholarship",
                    "kind": "scholarship",
                    "direction": "credit",
                    "term": "Spring 2027",
                }
            ]
        },
    )

    ledger = build_ledger([bill, award], today=date(2026, 10, 25))
    spring = ledger.terms["Spring 2027"]["USD"]

    assert spring.aid == Decimal("2500.00")
    assert spring.net_balance == Decimal("7500.00")
    assert [entry.amount for entry in spring.expected_not_yet_billed] == [
        Decimal("500.00")
    ]


def test_unmatched_housing_commitment_is_not_added_to_billed_charges() -> None:
    bill = make_document(
        "bill",
        DocumentType.TUITION_BILL,
        term="Fall 2026",
        envelope={
            "line_items": [
                {
                    "label": "Tuition",
                    "amount": "9000",
                    "category": "tuition",
                    "kind": "tuition",
                    "direction": "charge",
                }
            ]
        },
    )
    contract = make_document(
        "contract",
        DocumentType.HOUSING_CONTRACT,
        term="2026-2027 Academic Year",
        envelope={
            "line_items": [
                {
                    "label": "Spring room rate",
                    "amount": "3300",
                    "category": "housing",
                    "kind": "housing",
                    "direction": "charge",
                    "term": "Spring 2027",
                }
            ]
        },
    )

    ledger = build_ledger([bill, contract], today=date(2026, 10, 25))

    assert ledger.terms["Spring 2027"]["USD"].charges == Decimal(0)
    assert ledger.terms["Spring 2027"]["USD"].committed_not_yet_billed[0].amount == Decimal(
        "3300.00"
    )


def test_payment_plan_installments_are_scheduled_not_received_payments() -> None:
    bill = make_document(
        "spring-bill",
        DocumentType.TUITION_BILL,
        term="Spring 2027",
        envelope={
            "line_items": [
                {
                    "label": "Tuition",
                    "amount": "6450",
                    "category": "tuition",
                    "kind": "tuition",
                    "direction": "charge",
                    "term": "Spring 2027",
                }
            ]
        },
    )
    plan = make_document(
        "spring-plan",
        DocumentType.PAYMENT_PLAN,
        term="Spring 2027",
        envelope={
            "total_amount": "6450",
            "line_items": [
                {
                    "label": f"Installment {index}",
                    "amount": "1500",
                    "category": "payment",
                    "kind": "payment",
                    "direction": "credit",
                    "term": "Spring 2027",
                }
                for index in range(1, 5)
            ],
        },
    )

    ledger = build_ledger([bill, plan], today=date(2026, 10, 25))
    spring = ledger.terms["Spring 2027"]["USD"]

    assert spring.payments == Decimal(0)
    assert spring.net_balance == Decimal("6450.00")
    assert sum((entry.amount for entry in spring.scheduled_coverage), Decimal(0)) == Decimal(
        "6000.00"
    )
