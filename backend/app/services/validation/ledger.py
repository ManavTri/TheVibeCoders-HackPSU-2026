"""Deterministic, term-aware financial ledger construction."""

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Any, Literal

from app.schemas.documents import DocumentType, FinancialDocument, LineItem
from app.services.validation.normalize import (
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
            "net_balance": str(self.net_balance),
            "coverage_ratio": (
                str(self.coverage_ratio.quantize(Decimal("0.0001")))
                if self.coverage_ratio is not None
                else None
            ),
            "gap": str(quantize_money(self.gap)),
            "surplus": str(quantize_money(self.surplus)),
            "provenance": [entry.as_dict() for entry in self.entries],
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


def build_ledger(documents: list[FinancialDocument], today: date) -> Ledger:
    """Build balances from active extracted documents without persistence or I/O."""
    _ = today
    terms: dict[str, dict[str, LedgerTotals]] = {}
    annual: dict[str, dict[str, LedgerTotals]] = {}
    total: dict[str, LedgerTotals] = {}
    estimates: list[LedgerEntry] = []

    for document in documents:
        envelope = document.extraction_envelope or {}
        currency = str(envelope.get("currency") or document.currency or "USD")
        items = [
            LineItem.model_validate(item)
            for item in envelope.get("line_items", [])
            if isinstance(item, dict) and item.get("amount") is not None
        ]
        document_terms = envelope.get("terms")
        if not isinstance(document_terms, list):
            document_terms = []
        document_terms = [term for term in document_terms if isinstance(term, str)]
        disbursements = envelope.get("disbursements", [])
        document_entries: list[LedgerEntry] = []

        for item in items:
            classification = classify_line_item(item)
            is_estimate = _is_estimate(document, item)
            assignment = assign_item_term(
                item_term=item.term,
                document_term=document.term,
                document_terms=document_terms,
                item_date=item.date,
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
                source="line_item",
                confidence=classification.confidence,
                entry_date=item.date,
            )
            if is_estimate:
                estimates.append(item_entry)
            elif classification.direction != "unknown":
                document_entries.append(item_entry)

        if not items:
            legacy = _legacy_entry(document, currency)
            if legacy is not None:
                assignment = assign_item_term(
                    item_term=None,
                    document_term=document.term,
                    document_terms=document_terms,
                    item_date=document.deadline,
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
                else:
                    document_entries.append(legacy)

        for raw_disbursement in disbursements:
            if not isinstance(raw_disbursement, dict) or raw_disbursement.get("amount") is None:
                continue
            disbursement = _entry(
                document,
                label=str(raw_disbursement.get("award_label") or "Expected disbursement"),
                amount=Decimal(str(raw_disbursement["amount"])),
                currency=currency,
                kind="disbursement",
                direction="credit",
                term=None,
                source="disbursement",
            )
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
            if not items and not document_entries:
                document_entries.append(disbursement)
            elif assignment.term and assignment.term.is_known:
                term_totals = _get_buckets(terms, str(assignment.term), currency)
                term_totals.expected_disbursements.append(disbursement)
            elif assignment.annual_unallocated:
                year = _year_key(document)
                _get_buckets(annual, year, currency).expected_disbursements.append(disbursement)

        for entry in document_entries:
            total.setdefault(entry.currency, LedgerTotals(None, entry.currency)).add(entry)
            if entry.term is not None:
                _get_buckets(terms, entry.term, entry.currency).add(entry)
            elif document.term or document_terms:
                year = _year_key(document)
                _get_buckets(annual, year, entry.currency).add(entry)

    for currencies in terms.values():
        for totals in currencies.values():
            totals.expected_disbursements.sort(key=lambda entry: entry.date or "")
    for totals in total.values():
        totals.expected_disbursements.sort(key=lambda entry: entry.date or "")
    return Ledger(terms=terms, total=total, annual_unallocated=annual, estimates=estimates)
