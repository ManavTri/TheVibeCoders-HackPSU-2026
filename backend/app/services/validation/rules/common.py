from datetime import date
from decimal import Decimal
from typing import Any, Literal

from app.schemas.documents import DocumentType, FinancialDocument, LineItem
from app.schemas.validation import Finding, FindingEvidence, Severity
from app.services.validation.ledger import Ledger, LedgerEntry
from app.services.validation.normalize import Term, parse_terms

Category = Literal[
    "amount",
    "timing",
    "eligibility",
    "duplicate",
    "coverage",
    "data_quality",
    "opportunity",
]


def document_lines(document: FinancialDocument) -> list[LineItem]:
    raw_items = (document.extraction_envelope or {}).get("line_items", [])
    result: list[LineItem] = []
    if not isinstance(raw_items, list):
        return result
    for raw_item in raw_items:
        if not isinstance(raw_item, dict):
            continue
        try:
            result.append(LineItem.model_validate(raw_item))
        except ValueError:
            continue
    return result


def document_term(document: FinancialDocument) -> Term:
    parsed = parse_terms(document.term)
    if len(parsed.terms) == 1:
        return parsed.terms[0]
    envelope_terms = (document.extraction_envelope or {}).get("terms", [])
    if isinstance(envelope_terms, list):
        candidates = [
            term
            for value in envelope_terms
            if isinstance(value, str)
            for term in parse_terms(value).terms
            if term.is_known
        ]
        if len(set(candidates)) == 1:
            return candidates[0]
    return Term.unknown()


def document_entries(ledger: Ledger, document_id: str) -> list[LedgerEntry]:
    return [
        entry
        for totals in ledger.total.values()
        for entry in totals.entries
        if entry.document_id == document_id
    ]


def document_estimates(ledger: Ledger, document_id: str) -> list[LedgerEntry]:
    return [entry for entry in ledger.estimates if entry.document_id == document_id]


def evidence_for_entry(
    entry: LedgerEntry, *, field: str = "line_items", value: Any | None = None
) -> FindingEvidence:
    return FindingEvidence(
        document_id=entry.document_id,
        filename=entry.filename,
        field=field,
        label=entry.label,
        value=entry.amount if value is None else value,
    )


def evidence_for_document(
    document: FinancialDocument, field: str, label: str, value: Any = None
) -> FindingEvidence:
    return FindingEvidence(
        document_id=document.id,
        filename=document.filename,
        field=field,
        label=label,
        value=value,
    )


def build_finding(
    *,
    rule_id: str,
    severity: Severity,
    category: Category,
    title: str,
    explanation: str,
    evidence: list[FindingEvidence],
    suggested_action: str,
    document_ids: list[str] | None = None,
    term: str | None = None,
    impact_amount: Decimal | None = None,
    confidence: Literal["high", "medium", "low"] = "high",
    group_key: str,
    fields: dict[str, Any] | None = None,
    nearest_deadline: date | None = None,
    via: str | None = None,
) -> Finding:
    values = dict(fields or {})
    if nearest_deadline:
        values["nearest_deadline"] = nearest_deadline.isoformat()
    return Finding(
        rule_id=rule_id,
        severity=severity,
        category=category,
        title=title,
        explanation=explanation,
        document_ids=sorted(set(document_ids or [item.document_id for item in evidence])),
        fields=values,
        suggested_action=suggested_action,
        evidence=evidence,
        term=term,
        impact_amount=impact_amount,
        confidence=confidence,
        group_key=group_key,
        via=via,
    )


def format_money(amount: Decimal, currency: str = "USD") -> str:
    formatted = f"{amount:,.2f}"
    return f"${formatted}" if currency == "USD" else f"{currency} {formatted}"


def is_award_type(document: FinancialDocument) -> bool:
    return document.document_type in {
        DocumentType.AWARD_LETTER,
        DocumentType.FINANCIAL_AID_PACKAGE,
    }


def deadline_records(
    documents: list[FinancialDocument],
) -> list[tuple[FinancialDocument, str, date, str | None]]:
    records: list[tuple[FinancialDocument, str, date, str | None]] = []
    for document in documents:
        envelope = document.extraction_envelope or {}
        for field in ("deadlines", "payment_due_dates"):
            items = envelope.get(field, [])
            if not isinstance(items, list):
                continue
            for item in items:
                if not isinstance(item, dict) or not item.get("date"):
                    continue
                try:
                    deadline = date.fromisoformat(str(item["date"]))
                except ValueError:
                    continue
                label = str(item.get("label") or "Deadline")
                term = item.get("term") or document.term
                records.append((document, label, deadline, str(term) if term else None))
        document_dates = {record[2] for record in records if record[0].id == document.id}
        if document.deadline and document.deadline not in document_dates:
            records.append((document, "Due date", document.deadline, document.term))
    return records


def term_matches(first: str | None, second: str | None) -> bool:
    if not first or not second:
        return False
    first_terms = [term for term in parse_terms(first).terms if term.is_known]
    second_terms = [term for term in parse_terms(second).terms if term.is_known]
    return len(first_terms) == len(second_terms) == 1 and first_terms[0] == second_terms[0]
