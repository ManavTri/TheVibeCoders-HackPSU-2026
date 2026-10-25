from datetime import date
from decimal import Decimal

import pytest

from app.schemas.documents import LineItem
from app.services.validation.normalize import (
    AcademicCalendar,
    Term,
    assign_item_term,
    classify_line_item,
    infer_term,
    match_awards,
    normalize_award_name,
    parse_term,
    parse_terms,
    quantize_money,
)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("Fall 2026", ["Fall 2026"]),
        ("Fall 26", ["Fall 2026"]),
        ("FA26", ["Fall 2026"]),
        ("Fall Semester 2026", ["Fall 2026"]),
        ("2026 Fall", ["Fall 2026"]),
        ("Spring/Fall 2026-27", ["Fall 2026", "Spring 2027"]),
        ("Academic Year 2026-2027", ["Fall 2026", "Spring 2027"]),
        ("AY 26-27", ["Fall 2026", "Spring 2027"]),
        ("2026-27", ["Fall 2026", "Spring 2027"]),
        ("2026-2027 Academic Year", ["Fall 2026", "Spring 2027"]),
        ("2026-27 Academic Year", ["Fall 2026", "Spring 2027"]),
        ("Spring Semester 2027", ["Spring 2027"]),
        ("SP27", ["Spring 2027"]),
        ("SU27", ["Summer 2027"]),
    ],
)
def test_parse_term_formats(value: str, expected: list[str]) -> None:
    assert [str(term) for term in parse_terms(value).terms] == expected


@pytest.mark.parametrize("value", ["", "Winter 2026", "Q1 2026", "nonsense"])
def test_unparseable_terms_are_unknown(value: str) -> None:
    assert parse_term(value) == Term.unknown()


def test_academic_year_only_includes_summer_when_explicitly_stated() -> None:
    parsed = parse_terms("Academic Year 2026-2027")
    assert parsed.summer_included is False
    assert all(term.season != "summer" for term in parsed.terms)


@pytest.mark.parametrize(
    ("day", "expected"),
    [
        (date(2026, 8, 1), "Fall 2026"),
        (date(2027, 1, 15), "Spring 2027"),
        (date(2027, 6, 15), "Summer 2027"),
    ],
)
def test_date_term_inference(day: date, expected: str) -> None:
    inferred = infer_term(day)
    assert str(inferred) == expected
    assert inferred.inferred


def test_custom_calendar_changes_inference_boundaries() -> None:
    inferred = infer_term(
        date(2026, 7, 15),
        AcademicCalendar(fall_start_month=7, spring_start_month=1, summer_start_month=6),
    )
    assert str(inferred) == "Fall 2026"


def test_item_assignment_prioritizes_explicit_terms_and_annual_unallocated() -> None:
    explicit = assign_item_term(item_term="Spring 2027", document_term="Fall 2026")
    assert str(explicit.term) == "Spring 2027"

    annual = assign_item_term(
        item_term=None,
        document_term=None,
        document_terms=["Academic Year 2026-2027"],
    )
    assert annual.term is None
    assert annual.annual_unallocated

    inferred = assign_item_term(
        item_term=None,
        document_term=None,
        item_date=date(2026, 10, 1),
    )
    assert str(inferred.term) == "Fall 2026"
    assert inferred.term.inferred


@pytest.mark.parametrize(
    ("item", "kind", "direction", "confidence"),
    [
        (LineItem(label="Tuition charge", amount=100, category="cost"), "tuition", "charge", "high"),
        (LineItem(label="Scholarship credit", amount=100, category="aid"), "scholarship", "credit", "high"),
        (LineItem(label="Mystery item", amount=100, category="misc"), "other", "unknown", "low"),
        (
            LineItem(label="Miscellaneous", amount=100, category="misc", direction="credit"),
            "other",
            "credit",
            "low",
        ),
    ],
)
def test_line_item_classification(item, kind, direction, confidence) -> None:
    classification = classify_line_item(item)
    assert (classification.kind, classification.direction, classification.confidence) == (
        kind,
        direction,
        confidence,
    )


def test_award_name_matching_tiers_and_name_normalization() -> None:
    assert normalize_award_name("The University Endowed Scholarship of Hope") == frozenset(
        {"hope"}
    )
    exact = match_awards(
        name_a="Hope Scholarship",
        term_a="Fall 2026",
        amount_a=Decimal(1000),
        name_b="Hope Award",
        term_b="Fall 2026",
        amount_b=Decimal(1000),
    )
    assert exact.tier == "high"

    fuzzy = match_awards(
        name_a="Hope Student",
        term_a="Fall 2026",
        amount_a=Decimal(1000),
        name_b="Hope Students",
        term_b="Fall 2026",
        amount_b=Decimal(900),
    )
    assert fuzzy.tier == "medium"

    amount_only = match_awards(
        name_a="Academic Promise",
        term_a="Fall 2026",
        amount_a=Decimal(1000),
        name_b="Engineering Excellence",
        term_b="Fall 2026",
        amount_b=Decimal(1000),
    )
    assert amount_only.tier == "low"


def test_money_is_quantized_to_cents() -> None:
    assert quantize_money("1.005") == Decimal("1.01")
