"""Pure normalization helpers for financial validation."""

import re
import string
from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from difflib import SequenceMatcher
from functools import total_ordering
from typing import Literal

from app.schemas.documents import LineItem

_SEASONS = {"fall": 0, "spring": 1, "summer": 2}
_SEASON_PATTERN = re.compile(r"\b(fall|autumn|spring|summer)\b", re.IGNORECASE)
_SEASON_CODE_PATTERN = re.compile(r"\b(FA|SP|SU)(\d{2})\b", re.IGNORECASE)
_YEAR_RANGE_PATTERN = re.compile(r"\b(20\d{2}|\d{2})\s*[-/]\s*(20\d{2}|\d{2})\b")
_AY_PREFIX_PATTERN = re.compile(r"\b(?:academic\s+year|ay)\s*", re.IGNORECASE)
_STOPWORDS = {
    "scholarship",
    "grant",
    "award",
    "fund",
    "the",
    "of",
    "university",
    "endowed",
}
_KIND_DIRECTIONS: dict[str, Literal["charge", "credit", "unknown"]] = {
    "tuition": "charge",
    "fees": "charge",
    "housing": "charge",
    "meals": "charge",
    "books": "charge",
    "travel": "charge",
    "program_fee": "charge",
    "insurance": "charge",
    "other_charge": "charge",
    "scholarship": "credit",
    "grant": "credit",
    "loan": "credit",
    "work_study": "credit",
    "waiver": "credit",
    "payment": "credit",
    "refund": "credit",
    "other": "unknown",
}
_KEYWORDS: tuple[tuple[tuple[str, ...], str, Literal["charge", "credit", "unknown"]], ...] = (
    (("tuition",), "tuition", "charge"),
    (("fee", "fees"), "fees", "charge"),
    (("housing", "residence hall", "dorm"), "housing", "charge"),
    (("meal", "dining"), "meals", "charge"),
    (("book", "textbook"), "books", "charge"),
    (("travel", "airfare"), "travel", "charge"),
    (("program fee", "program cost"), "program_fee", "charge"),
    (("insurance",), "insurance", "charge"),
    (("scholarship",), "scholarship", "credit"),
    (("grant",), "grant", "credit"),
    (("loan",), "loan", "credit"),
    (("work-study", "work study"), "work_study", "credit"),
    (("waiver",), "waiver", "credit"),
    (("payment", "paid"), "payment", "credit"),
    (("refund",), "refund", "credit"),
)


@total_ordering
@dataclass(frozen=True)
class Term:
    season: str | None
    year: int | None
    inferred: bool = False

    @classmethod
    def unknown(cls) -> "Term":
        return cls(None, None)

    @property
    def is_known(self) -> bool:
        return self.season in _SEASONS and self.year is not None

    @property
    def sort_key(self) -> tuple[int, int]:
        if not self.is_known:
            return (10**9, 10**9)
        return (self.year or 0, _SEASONS[self.season or ""])

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, Term):
            return NotImplemented
        return self.sort_key < other.sort_key

    def __str__(self) -> str:
        if not self.is_known:
            return "unknown"
        return f"{self.season.title()} {self.year}"


@dataclass(frozen=True)
class ParsedTerms:
    terms: tuple[Term, ...]
    summer_included: bool = False
    academic_year: tuple[int, int] | None = None


@dataclass(frozen=True)
class TermAssignment:
    term: Term | None
    annual_unallocated: bool = False


@dataclass(frozen=True)
class ItemClassification:
    kind: str
    direction: Literal["charge", "credit", "unknown"]
    confidence: Literal["high", "low"]


@dataclass(frozen=True)
class AwardMatch:
    tier: Literal["high", "medium", "low", "none"]
    similarity: float


def _year_number(value: str) -> int:
    year = int(value)
    return 2000 + year if year < 100 else year


def _expand_year_range(match: re.Match[str]) -> tuple[int, int]:
    first = _year_number(match.group(1))
    raw_second = int(match.group(2))
    if raw_second < 100:
        second = first // 100 * 100 + raw_second
        if second < first:
            second += 100
    else:
        second = raw_second
    return first, second


def _year_from_text(text: str) -> int | None:
    range_match = _YEAR_RANGE_PATTERN.search(text)
    if range_match:
        return _expand_year_range(range_match)[0]
    years = re.findall(r"\b(?:20\d{2}|\d{2})\b", text)
    return _year_number(years[-1]) if years else None


def parse_terms(value: str | None) -> ParsedTerms:
    if not value or not value.strip():
        return ParsedTerms((Term.unknown(),))
    text = value.strip()
    code_match = _SEASON_CODE_PATTERN.search(text)
    if code_match:
        season = {"fa": "fall", "sp": "spring", "su": "summer"}[
            code_match.group(1).casefold()
        ]
        return ParsedTerms((Term(season, _year_number(code_match.group(2))),))
    normalized = _AY_PREFIX_PATTERN.sub("", text).strip()
    range_match = _YEAR_RANGE_PATTERN.search(normalized)
    year_range = _expand_year_range(range_match) if range_match else None
    season_matches = [match.group(1).casefold() for match in _SEASON_PATTERN.finditer(normalized)]
    year = _year_from_text(normalized)
    if year is None:
        return ParsedTerms((Term.unknown(),))

    has_academic_year_marker = bool(_AY_PREFIX_PATTERN.search(text))
    if year_range and (
        has_academic_year_marker
        or len(season_matches) > 1
        or not season_matches
        or re.fullmatch(r"\s*(?:20\d{2}|\d{2})\s*[-/]\s*(?:20\d{2}|\d{2})\s*", normalized)
    ):
        start, end = year_range
        terms = (Term("fall", start), Term("spring", end))
        summer = "summer" in season_matches
        if summer:
            terms = (Term("fall", start), Term("spring", end), Term("summer", end))
        return ParsedTerms(terms, summer_included=summer, academic_year=(start, end))

    if season_matches:
        terms: list[Term] = []
        for season in season_matches:
            canonical_season = "fall" if season == "autumn" else season
            season_year = year
            if year_range and canonical_season == "spring":
                season_year = year_range[1]
            terms.append(Term(canonical_season, season_year))
        return ParsedTerms(tuple(sorted(set(terms))), academic_year=year_range)

    if year_range:
        start, end = year_range
        return ParsedTerms((Term("fall", start), Term("spring", end)), academic_year=(start, end))
    return ParsedTerms((Term.unknown(),))


def parse_term(value: str | None) -> Term:
    terms = parse_terms(value).terms
    return terms[0] if len(terms) == 1 else Term.unknown()


@dataclass(frozen=True)
class AcademicCalendar:
    fall_start_month: int = 8
    spring_start_month: int = 1
    summer_start_month: int = 6


def infer_term(value: date, calendar: AcademicCalendar | None = None) -> Term:
    calendar = calendar or AcademicCalendar()
    month = value.month
    if calendar.fall_start_month <= month <= 12:
        return Term("fall", value.year, inferred=True)
    if calendar.spring_start_month <= month < calendar.summer_start_month:
        return Term("spring", value.year, inferred=True)
    return Term("summer", value.year, inferred=True)


def assign_item_term(
    *,
    item_term: str | None,
    document_term: str | None,
    document_terms: list[str] | None = None,
    item_date: date | None = None,
    calendar: AcademicCalendar | None = None,
) -> TermAssignment:
    if item_term:
        parsed = parse_terms(item_term).terms
        return TermAssignment(parsed[0] if len(parsed) == 1 else Term.unknown())
    terms = [
        term
        for raw_term in (document_terms or [])
        for term in parse_terms(raw_term).terms
        if term.is_known
    ]
    if len(set(terms)) > 1:
        return TermAssignment(None, annual_unallocated=True)
    if document_term:
        parsed = parse_terms(document_term).terms
        if len(parsed) > 1:
            return TermAssignment(None, annual_unallocated=True)
        return TermAssignment(parsed[0])
    if terms:
        return TermAssignment(terms[0])
    if item_date:
        return TermAssignment(infer_term(item_date, calendar))
    return TermAssignment(None)


def classify_line_item(item: LineItem) -> ItemClassification:
    if item.kind:
        direction = item.direction or _KIND_DIRECTIONS[item.kind]
        return ItemClassification(item.kind, direction, "high")
    if item.direction in {"charge", "credit"}:
        for keywords, kind, _ in _KEYWORDS:
            if any(keyword in f"{item.label} {item.category}".casefold() for keyword in keywords):
                return ItemClassification(kind, item.direction, "high")
        return ItemClassification("other", item.direction, "low")
    text = f"{item.label} {item.category}".casefold()
    for keywords, kind, direction in _KEYWORDS:
        if any(keyword in text for keyword in keywords):
            return ItemClassification(kind, direction, "high")
    return ItemClassification("other", "unknown", "low")


def normalize_award_name(value: str) -> frozenset[str]:
    normalized = value.casefold().translate(str.maketrans("", "", string.punctuation))
    return frozenset(
        token for token in normalized.split() if token and token not in _STOPWORDS
    )


def match_awards(
    *,
    name_a: str,
    term_a: str | None,
    amount_a: Decimal | None,
    name_b: str,
    term_b: str | None,
    amount_b: Decimal | None,
    fuzzy_threshold: float = 0.85,
) -> AwardMatch:
    normalized_a = normalize_award_name(name_a)
    normalized_b = normalize_award_name(name_b)
    parsed_a = parse_term(term_a)
    parsed_b = parse_term(term_b)
    same_term = parsed_a.is_known and parsed_a == parsed_b
    union = normalized_a | normalized_b
    token_similarity = len(normalized_a & normalized_b) / len(union) if union else 0.0
    sequence_similarity = SequenceMatcher(
        None, " ".join(sorted(normalized_a)), " ".join(sorted(normalized_b))
    ).ratio()
    similarity = max(token_similarity, sequence_similarity)
    if same_term and normalized_a == normalized_b and normalized_a:
        return AwardMatch("high", 1.0)
    if same_term and similarity >= fuzzy_threshold:
        return AwardMatch("medium", similarity)
    if amount_a is not None and amount_b is not None and quantize_money(amount_a) == quantize_money(amount_b):
        return AwardMatch("low", similarity)
    return AwardMatch("none", similarity)


def quantize_money(value: Decimal | str | float) -> Decimal:
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError("Money values must be valid decimals.") from exc
    if not amount.is_finite():
        raise ValueError("Money values must be finite.")
    return amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
