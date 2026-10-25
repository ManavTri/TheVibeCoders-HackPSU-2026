"""Deterministic, term-aware financial ledger construction."""

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Any, Literal

from app.schemas.documents import DocumentType, FinancialDocument, LineItem
from app.services.validation.normalize import (
    AcademicCalendar,
    assign_item_term,
    classify_line_item,
    parse_terms,
    quantize_money,
)

Direction = Literal["charge", "credit", "unknown"]


@dataclass(frozen=True)
class LedgerEntry:
    document_id: str
    filename: str
    label: str
    amount: Decimal
    currency: str
    kind: str
    direction: Direction
    term: str | None
    source: str
    confidence: str = "high"
    date: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "document_id": self.document_id,
            "filename": self.filename,
            "label": self.label,
            "amount": str(self.amount),
            "currency": self.currency,
            "kind": self.kind,
            "direction": self.direction,
            "term": self.term,
            "source": self.source,
            "confidence": self.confidence,
            "date": self.date,
        }


@dataclass
class LedgerTotals:
    term: str | None
    currency: str
    charges_by_kind: dict[str, Decimal] = field(default_factory=dict)
    aid_by_kind: dict[str, Decimal] = field(default_factory=dict)
    payments: Decimal = Decimal(0)
    expected_disbursements: list[LedgerEntry] = field(default_factory=list)
    entries: list[LedgerEntry] = field(default_factory=list)
    reference_entries: list[LedgerEntry] = field(default_factory=list)
    expected_not_yet_billed: list[LedgerEntry] = field(default_factory=list)
    committed_not_yet_billed: list[LedgerEntry] = field(default_factory=list)
    scheduled_coverage: list[LedgerEntry] = field(default_factory=list)

    @property
    def charges(self) -> Decimal:
        return sum(self.charges_by_kind.values(), Decimal(0))

    @property
    def aid(self) -> Decimal:
        return sum(self.aid_by_kind.values(), Decimal(0))

    @property
    def net_balance(self) -> Decimal:
        return quantize_money(self.charges - self.aid - self.payments)

    @property
    def coverage_ratio(self) -> Decimal | None:
        if self.charges == 0:
            return None
        return (self.aid + self.payments) / self.charges

    @property
    def gap(self) -> Decimal:
        return max(Decimal(0), self.net_balance)

    @property
    def surplus(self) -> Decimal:
        return max(Decimal(0), -self.net_balance)

    def add(self, entry: LedgerEntry) -> None:
        self.entries.append(entry)
        if entry.direction == "charge":
            self.charges_by_kind[entry.kind] = (
                self.charges_by_kind.get(entry.kind, Decimal(0)) + entry.amount
            )
        elif entry.kind == "payment":
            self.payments += entry.amount
        elif entry.direction == "credit":
            self.aid_by_kind[entry.kind] = (
                self.aid_by_kind.get(entry.kind, Decimal(0)) + entry.amount
            )

    def add_reference(self, entry: LedgerEntry, bucket: str) -> None:
        self.reference_entries.append(entry)
        if bucket != "reference_entries":
            getattr(self, bucket).append(entry)

    def as_dict(self) -> dict[str, Any]:
        return {
            "term": self.term,
            "currency": self.currency,
            "charges_by_kind": _money_map(self.charges_by_kind),
            "aid_by_kind": _money_map(self.aid_by_kind),
            "charges": str(quantize_money(self.charges)),
            "aid": str(quantize_money(self.aid)),
            "payments": str(quantize_money(self.payments)),
            "expected_disbursements": [
                entry.as_dict() for entry in self.expected_disbursements
            ],
            "expected_not_yet_billed": [
                entry.as_dict() for entry in self.expected_not_yet_billed
            ],
            "committed_not_yet_billed": [
                entry.as_dict() for entry in self.committed_not_yet_billed
            ],
            "scheduled_coverage": [
                entry.as_dict() for entry in self.scheduled_coverage
            ],
            "scheduled_coverage_total": str(
                quantize_money(
                    sum((entry.amount for entry in self.scheduled_coverage), Decimal(0))
                )
            ),
            "net_balance": str(self.net_balance),
            "coverage_ratio": (
                str(self.coverage_ratio.quantize(Decimal("0.0001")))
                if self.coverage_ratio is not None
                else None
            ),
            "gap": str(quantize_money(self.gap)),
            "surplus": str(quantize_money(self.surplus)),
            "provenance": [entry.as_dict() for entry in self.entries],
            "reference_entries": [
                entry.as_dict() for entry in self.reference_entries
            ],
        }


@dataclass
class Ledger:
    terms: dict[str, dict[str, LedgerTotals]]
    total: dict[str, LedgerTotals]
    annual_unallocated: dict[str, dict[str, LedgerTotals]]
    estimates: list[LedgerEntry]

    def as_dict(self) -> dict[str, Any]:
        return {
            "terms": {
                term: {currency: totals.as_dict() for currency, totals in currencies.items()}
                for term, currencies in self.terms.items()
            },
            "total": {currency: totals.as_dict() for currency, totals in self.total.items()},
            "annual_unallocated": {
                year: {
                    currency: totals.as_dict()
                    for currency, totals in currencies.items()
                }
                for year, currencies in self.annual_unallocated.items()
            },
            "estimates": [entry.as_dict() for entry in self.estimates],
        }


def _money_map(values: dict[str, Decimal]) -> dict[str, str]:
    return {kind: str(quantize_money(amount)) for kind, amount in sorted(values.items())}


def _year_key(document: FinancialDocument) -> str:
    envelope = document.extraction_envelope or {}
    raw_year = envelope.get("academic_year")
    parsed = parse_terms(str(raw_year)) if raw_year else parse_terms(document.term)
    if parsed.academic_year:
        return f"{parsed.academic_year[0]}-{parsed.academic_year[1]}"
    for term in parsed.terms:
        if term.is_known and term.year is not None:
            start = term.year if term.season == "fall" else term.year - 1
            return f"{start}-{start + 1}"
    return "unknown"


def _is_estimate(document: FinancialDocument, item: LineItem | None = None) -> bool:
    if document.document_type == DocumentType.STUDY_ABROAD_QUOTE:
        return True
    if item is None:
        return False
    label = f"{item.label} {item.category} {item.kind or ''}".casefold()
    return any(term in label for term in ("cost of attendance", "estimated cost", "program estimate"))


def _entry(
    document: FinancialDocument,
    *,
    label: str,
    amount: Decimal,
    currency: str,
    kind: str,
    direction: Direction,
    term: str | None,
    source: str,
    confidence: str = "high",
    entry_date: date | None = None,
) -> LedgerEntry:
    return LedgerEntry(
        document_id=document.id,
        filename=document.filename,
        label=label,
        amount=quantize_money(amount),
        currency=currency,
        kind=kind,
        direction=direction,
        term=term,
        source=source,
        confidence=confidence,
        date=entry_date.isoformat() if entry_date else None,
    )


def _legacy_entry(document: FinancialDocument, currency: str) -> LedgerEntry | None:
    if document.amount is None:
        return None
    defaults: dict[DocumentType, tuple[str, Direction]] = {
        DocumentType.AWARD_LETTER: ("scholarship", "credit"),
        DocumentType.TUITION_BILL: ("tuition", "charge"),
        DocumentType.LOAN_OFFER: ("loan", "credit"),
        DocumentType.HOUSING_CONTRACT: ("housing", "charge"),
    }
    classification = defaults.get(document.document_type)
    if classification is None:
        return None
    kind, direction = classification
    return _entry(
        document,
        label=f"Document total: {document.filename}",
        amount=document.amount,
        currency=currency,
        kind=kind,
        direction=direction,
        term=None,
        source="legacy_document_amount",
        confidence="low",
    )


def _get_buckets(
    mapping: dict[str, dict[str, LedgerTotals]], term: str, currency: str
) -> LedgerTotals:
    if term not in mapping:
        mapping[term] = {}
    if currency not in mapping[term]:
        mapping[term][currency] = LedgerTotals(term, currency)
    return mapping[term][currency]


def build_ledger(
    documents: list[FinancialDocument],
    today: date,
    calendar: AcademicCalendar | None = None,
) -> Ledger:
    """Build balances from active extracted documents without persistence or I/O."""
    _ = today
    terms: dict[str, dict[str, LedgerTotals]] = {}
    annual: dict[str, dict[str, LedgerTotals]] = {}
    total: dict[str, LedgerTotals] = {}
    estimates: list[LedgerEntry] = []
    actual_bill_entries: list[LedgerEntry] = []
    reference_entries: list[tuple[LedgerEntry, str]] = []
    scheduled_entries: list[LedgerEntry] = []
    document_years = {document.id: _year_key(document) for document in documents}

    for document in documents:
        envelope = document.extraction_envelope or {}
        currency = str(envelope.get("currency") or document.currency or "USD")
        raw_items = envelope.get("line_items", [])
        if not isinstance(raw_items, list):
            raw_items = []
        items = []
        for raw_item in raw_items:
            if not isinstance(raw_item, dict) or raw_item.get("amount") is None:
                continue
            try:
                items.append(LineItem.model_validate(raw_item))
            except ValueError:
                continue
        document_terms = envelope.get("terms")
        if not isinstance(document_terms, list):
            document_terms = []
        document_terms = [term for term in document_terms if isinstance(term, str)]
        disbursements = envelope.get("disbursements", [])
        if not isinstance(disbursements, list):
            disbursements = []
        for item in items:
            classification = classify_line_item(item)
            is_estimate = _is_estimate(document, item)
            assignment = assign_item_term(
                item_term=item.term,
                document_term=document.term,
                document_terms=document_terms,
                item_date=item.date,
                calendar=calendar,
            )
            term_name = (
                str(assignment.term)
                if assignment.term and assignment.term.is_known
                else None
            )
            item_currency = str(envelope.get("currency") or document.currency or "USD")
            item_entry = _entry(
                document,
                label=item.label,
                amount=item.amount,
                currency=item_currency,
                kind=classification.kind,
                direction=classification.direction,
                term=term_name,
                source=(
                    "billed_line_item"
                    if document.document_type == DocumentType.TUITION_BILL
                    else "line_item"
                ),
                confidence=classification.confidence,
                entry_date=item.date,
            )
            if is_estimate:
                estimates.append(item_entry)
            elif classification.direction != "unknown":
                if document.document_type == DocumentType.TUITION_BILL:
                    actual_bill_entries.append(item_entry)
                elif document.document_type in {
                    DocumentType.AWARD_LETTER,
                    DocumentType.FINANCIAL_AID_PACKAGE,
                    DocumentType.LOAN_OFFER,
                }:
                    reference_entries.append((item_entry, "expected_not_yet_billed"))
                elif document.document_type == DocumentType.HOUSING_CONTRACT:
                    reference_entries.append((item_entry, "committed_not_yet_billed"))
                elif document.document_type == DocumentType.PAYMENT_PLAN:
                    scheduled_entries.append(item_entry)
                    reference_entries.append((item_entry, "scheduled_coverage"))
                else:
                    reference_entries.append((item_entry, "committed_not_yet_billed"))

        if not items:
            legacy = _legacy_entry(document, currency)
            if legacy is not None:
                assignment = assign_item_term(
                    item_term=None,
                    document_term=document.term,
                    document_terms=document_terms,
                    item_date=document.deadline,
                    calendar=calendar,
                )
                legacy = LedgerEntry(
                    **{
                        **legacy.__dict__,
                        "term": (
                            str(assignment.term)
                            if assignment.term and assignment.term.is_known
                            else None
                        ),
                    }
                )
                if _is_estimate(document):
                    estimates.append(legacy)
                elif document.document_type == DocumentType.TUITION_BILL:
                    actual_bill_entries.append(legacy)
                elif document.document_type in {
                    DocumentType.AWARD_LETTER,
                    DocumentType.FINANCIAL_AID_PACKAGE,
                    DocumentType.LOAN_OFFER,
                }:
                    reference_entries.append((legacy, "expected_not_yet_billed"))
                elif document.document_type == DocumentType.HOUSING_CONTRACT:
                    reference_entries.append((legacy, "committed_not_yet_billed"))
                elif document.document_type == DocumentType.PAYMENT_PLAN:
                    reference_entries.append((legacy, "scheduled_coverage"))
                    scheduled_entries.append(legacy)
                else:
                    reference_entries.append((legacy, "committed_not_yet_billed"))

        for raw_disbursement in disbursements:
            if not isinstance(raw_disbursement, dict) or raw_disbursement.get("amount") is None:
                continue
            try:
                disbursement_amount = Decimal(str(raw_disbursement["amount"]))
                disbursement = _entry(
                    document,
                    label=str(raw_disbursement.get("award_label") or "Expected disbursement"),
                    amount=disbursement_amount,
                    currency=currency,
                    kind="disbursement",
                    direction="credit",
                    term=None,
                    source="disbursement",
                )
            except (ValueError, ArithmeticError):
                continue
            raw_term = raw_disbursement.get("term")
            raw_date = raw_disbursement.get("date")
            try:
                parsed_date = date.fromisoformat(str(raw_date)) if raw_date else None
            except ValueError:
                parsed_date = None
            assignment = assign_item_term(
                item_term=str(raw_term) if raw_term else None,
                document_term=document.term,
                document_terms=document_terms,
                item_date=parsed_date,
                calendar=calendar,
            )
            disbursement = LedgerEntry(
                **{
                    **disbursement.__dict__,
                    "term": (
                        str(assignment.term)
                        if assignment.term and assignment.term.is_known
                        else None
                    ),
                    "date": parsed_date.isoformat() if parsed_date else None,
                }
            )
            total.setdefault(currency, LedgerTotals(None, currency)).expected_disbursements.append(
                disbursement
            )
            if assignment.term and assignment.term.is_known:
                term_totals = _get_buckets(terms, str(assignment.term), currency)
                term_totals.expected_disbursements.append(disbursement)
            elif assignment.annual_unallocated:
                year = _year_key(document)
                _get_buckets(annual, year, currency).expected_disbursements.append(disbursement)

    bill_credits = [
        entry for entry in actual_bill_entries if entry.direction == "credit"
    ]
    for entry in actual_bill_entries:
        total.setdefault(entry.currency, LedgerTotals(None, entry.currency)).add(entry)
        if entry.term is not None:
            _get_buckets(terms, entry.term, entry.currency).add(entry)
        elif document_years.get(entry.document_id) != "unknown":
            _get_buckets(
                annual, document_years[entry.document_id], entry.currency
            ).add(entry)

    bill_housing_keys = {
        (entry.term, entry.currency)
        for entry in actual_bill_entries
        if entry.kind == "housing" and entry.direction == "charge"
    }
    for entry, bucket in reference_entries:
        target_bucket = "reference_entries"
        if bucket == "committed_not_yet_billed" and entry.kind == "housing":
            if (entry.term, entry.currency) in bill_housing_keys:
                target_bucket = "reference_entries"
            else:
                target_bucket = "committed_not_yet_billed"
        if bucket == "expected_not_yet_billed":
            matching_credits = []
            for credit in bill_credits:
                from app.services.validation.normalize import match_awards

                match = match_awards(
                    name_a=entry.label,
                    term_a=entry.term,
                    amount_a=entry.amount,
                    name_b=credit.label,
                    term_b=credit.term,
                    amount_b=credit.amount,
                )
                if (
                    entry.currency == credit.currency
                    and entry.kind == credit.kind
                    and match.tier in {"high", "medium"}
                ):
                    matching_credits.append(credit)
            billed_amount = sum(
                (credit.amount for credit in matching_credits), Decimal(0)
            )
            unbilled_amount = max(Decimal(0), entry.amount - billed_amount)
            if unbilled_amount > 0:
                expected_entry = LedgerEntry(
                    **{
                        **entry.__dict__,
                        "amount": quantize_money(unbilled_amount),
                        "source": "expected_not_yet_billed",
                    }
                )
                _store_reference(
                    expected_entry,
                    "expected_not_yet_billed",
                    total,
                    terms,
                    annual,
                    document_years.get(entry.document_id),
                )
        if bucket == "scheduled_coverage":
            target_bucket = "scheduled_coverage"
        _store_reference(
            entry,
            target_bucket,
            total,
            terms,
            annual,
            document_years.get(entry.document_id),
        )

    for entry in scheduled_entries:
        total.setdefault(entry.currency, LedgerTotals(None, entry.currency))
        if entry.term is not None:
            _get_buckets(terms, entry.term, entry.currency)

    for currencies in terms.values():
        for totals in currencies.values():
            totals.expected_disbursements.sort(key=lambda entry: entry.date or "")
    for totals in total.values():
        totals.expected_disbursements.sort(key=lambda entry: entry.date or "")
    return Ledger(terms=terms, total=total, annual_unallocated=annual, estimates=estimates)


def _store_reference(
    entry: LedgerEntry,
    bucket: str,
    total: dict[str, LedgerTotals],
    terms: dict[str, dict[str, LedgerTotals]],
    annual: dict[str, dict[str, LedgerTotals]],
    year: str | None,
) -> None:
    total.setdefault(entry.currency, LedgerTotals(None, entry.currency)).add_reference(
        entry, bucket
    )
    if entry.term is not None:
        _get_buckets(terms, entry.term, entry.currency).add_reference(entry, bucket)
    elif year and year != "unknown":
        _get_buckets(annual, year, entry.currency).add_reference(entry, bucket)
