from collections import defaultdict
from decimal import Decimal

from app.schemas.documents import DocumentType, FinancialDocument
from app.schemas.validation import Finding, Severity
from app.services.validation.normalize import parse_terms
from app.services.validation.rules.base import RuleContext
from app.services.validation.rules.common import (
    build_finding,
    deadline_records,
    document_entries,
    document_term,
    evidence_for_document,
    evidence_for_entry,
    format_money,
    is_award_type,
    term_matches,
)


def _payment_due(context: RuleContext, term: str) -> tuple[object, FinancialDocument | None]:
    matches = [
        (record[2], record[0])
        for record in deadline_records(context.documents)
        if term_matches(record[3], term)
        and any(token in record[1].casefold() for token in ("payment", "due"))
    ]
    return min(matches, default=(None, None), key=lambda item: item[0] or context.today)


def term_gap_findings(context: RuleContext) -> list[Finding]:
    return _term_balance_findings(context, include="gap")


def term_surplus_findings(context: RuleContext) -> list[Finding]:
    return _term_balance_findings(context, include="surplus")


def currency_findings(context: RuleContext) -> list[Finding]:
    return _currency_findings(context)


def cost_of_attendance_findings(context: RuleContext) -> list[Finding]:
    return _cost_of_attendance_findings(context)


def _term_balance_findings(context: RuleContext, *, include: str) -> list[Finding]:
    findings: list[Finding] = []
    all_totals = [
        (term, currency, totals)
        for term, currencies in context.ledger.terms.items()
        for currency, totals in currencies.items()
    ]
    gaps = [
        (term, currency, totals)
        for term, currency, totals in all_totals
        if totals.charges > 0 and totals.gap > context.config.money_tolerance
    ]
    for term, currency, totals in all_totals:
        if include == "gap" and totals.charges <= 0:
            continue
        due_date, due_document = _payment_due(context, term)
        if include == "gap" and totals.gap > context.config.money_tolerance:
            overdue = due_date is not None and due_date < context.today
            disbursement_total = sum(
                (item.amount for item in totals.expected_disbursements), Decimal(0)
            )
            closes_gap = disbursement_total >= totals.gap
            pending_text = ""
            if totals.expected_disbursements:
                earliest = min(
                    (item.date for item in totals.expected_disbursements if item.date),
                    default=None,
                )
                pending_text = (
                    f" Listed pending disbursements total {format_money(disbursement_total, currency)}"
                    + (f", with the first dated {earliest}." if earliest else ".")
                )
            largest = sorted(
                (entry for entry in totals.entries if entry.direction == "charge"),
                key=lambda entry: entry.amount,
                reverse=True,
            )[:3]
            evidence = [evidence_for_entry(entry) for entry in largest]
            evidence.extend(
                evidence_for_entry(entry)
                for entry in totals.entries
                if entry.direction == "credit" or entry.kind == "payment"
            )
            if due_document and due_date:
                evidence.append(
                    evidence_for_document(
                        due_document,
                        "payment_due_dates",
                        "Payment due",
                        due_date.isoformat(),
                    )
                )
            findings.append(
                build_finding(
                    rule_id="coverage.term_gap",
                    severity=Severity.ERROR if overdue else Severity.WARNING,
                    category="coverage",
                    title=f"{term} has a {format_money(totals.gap, currency)} unpaid balance",
                    explanation=(
                        f"{term} charges total {format_money(totals.charges, currency)} "
                        f"and listed aid/payments total {format_money(totals.aid + totals.payments, currency)}, "
                        f"leaving {format_money(totals.gap, currency)}. The largest billed line is "
                        f"{largest[0].label if largest else 'not itemized'}."
                        + (
                            f" Payment is due {due_date.isoformat()}."
                            if due_date
                            else " No payment due date was found."
                        )
                        + pending_text
                    ),
                    evidence=evidence or [
                        evidence_for_document(
                            next(doc for doc in context.documents if doc.id == item.document_id),
                            "term",
                            term,
                            term,
                        )
                        for item in totals.entries[:1]
                    ],
                    suggested_action=(
                        f"Ask the billing office to confirm the {term} balance and payment deadline"
                        + (f" before {due_date.isoformat()}." if due_date else " before paying.")
                    ),
                    document_ids=[entry.document_id for entry in totals.entries],
                    term=term,
                    impact_amount=totals.gap,
                    confidence="high",
                    group_key=f"{term}:{currency}",
                    fields={
                        "currency": currency,
                        "charges": totals.charges,
                        "aid_and_payments": totals.aid + totals.payments,
                        "pending_disbursements_close_gap": closes_gap,
                        "payment_due_date": due_date.isoformat() if due_date else None,
                    },
                    nearest_deadline=due_date,
                )
            )
        elif include == "surplus" and totals.surplus > context.config.money_tolerance:
            other_gap = next((gap for gap in gaps if gap[0] != term), None)
            suggested_action = (
                f"Ask the financial-aid office whether the {term} surplus can be applied to {other_gap[0]}."
                if other_gap
                else f"Ask the financial-aid office whether the {term} surplus is refundable or remains as an account credit."
            )
            evidence = [evidence_for_entry(entry) for entry in totals.entries]
            findings.append(
                build_finding(
                    rule_id="coverage.term_surplus",
                    severity=Severity.INFO,
                    category="coverage",
                    title=f"{term} shows a {format_money(totals.surplus, currency)} surplus",
                    explanation=(
                        f"Listed aid/payments of {format_money(totals.aid + totals.payments, currency)} "
                        f"exceed billed charges of {format_money(totals.charges, currency)} by "
                        f"{format_money(totals.surplus, currency)} for {term}. This may be a refund or "
                        "account credit; the records do not determine which."
                    ),
                    evidence=evidence,
                    suggested_action=suggested_action,
                    term=term,
                    impact_amount=totals.surplus,
                    confidence="medium",
                    group_key=f"{term}:{currency}",
                    fields={"currency": currency, "surplus": totals.surplus},
                )
            )
    return findings


def _currency_findings(context: RuleContext) -> list[Finding]:
    findings: list[Finding] = []
    for term, currencies in context.ledger.terms.items():
        if len(currencies) < 2:
            continue
        entries = [entry for totals in currencies.values() for entry in totals.entries]
        document_ids = sorted({entry.document_id for entry in entries})
        documents = [doc for doc in context.documents if doc.id in document_ids]
        has_rate = any(
            (doc.extraction_envelope or {}).get("exchange_rate") is not None for doc in documents
        )
        if has_rate:
            continue
        evidence = [evidence_for_entry(entry) for entry in entries]
        findings.append(
            build_finding(
                rule_id="currency.mismatch",
                severity=Severity.WARNING,
                category="data_quality",
                title=f"{term} contains amounts in multiple currencies",
                explanation=(
                    f"{term} has ledger entries in {', '.join(sorted(currencies))}. These amounts "
                    "were kept separate because no stated exchange rate was found."
                ),
                evidence=evidence,
                suggested_action=(
                    f"Confirm the billing currency and obtain a documented exchange rate before comparing {term} totals."
                ),
                document_ids=document_ids,
                term=term,
                confidence="high",
                group_key=term,
                fields={"currencies": sorted(currencies)},
            )
        )
    return findings


def _cost_of_attendance_findings(context: RuleContext) -> list[Finding]:
    findings: list[Finding] = []
    estimates = [
        entry
        for entry in context.ledger.estimates
        if any(
            doc.id == entry.document_id and doc.document_type == DocumentType.FINANCIAL_AID_PACKAGE
            for doc in context.documents
        )
    ]
    aid_by_year: dict[tuple[str, str], list] = defaultdict(list)
    for document in context.documents:
        if not is_award_type(document):
            continue
        for entry in document_entries(context.ledger, document.id):
            if entry.direction == "credit" and entry.kind != "payment":
                year = _academic_year(document)
                aid_by_year[(year, entry.currency)].append(entry)
    for estimate in estimates:
        document = next(doc for doc in context.documents if doc.id == estimate.document_id)
        year = _academic_year(document)
        aid_entries = aid_by_year.get((year, estimate.currency), [])
        aid_total = sum((entry.amount for entry in aid_entries), Decimal(0))
        excess = aid_total - estimate.amount
        if excess <= context.config.money_tolerance:
            continue
        evidence = [evidence_for_entry(estimate)]
        evidence.extend(evidence_for_entry(entry) for entry in aid_entries)
        findings.append(
            build_finding(
                rule_id="coverage.over_cost_of_attendance",
                severity=Severity.WARNING,
                category="coverage",
                title=f"Aid exceeds the stated {year} cost estimate by {format_money(excess, estimate.currency)}",
                explanation=(
                    f"The aid entries total {format_money(aid_total, estimate.currency)} for {year}, "
                    f"while {document.filename} lists a cost-of-attendance estimate of "
                    f"{format_money(estimate.amount, estimate.currency)}. The difference is "
                    f"{format_money(excess, estimate.currency)}; the estimate is not a billed balance."
                ),
                evidence=evidence,
                suggested_action=(
                    "Ask the financial-aid office whether any aid adjustment is needed; loans may be reduced, "
                    "but the school must confirm its calculation."
                ),
                document_ids=[estimate.document_id, *(entry.document_id for entry in aid_entries)],
                impact_amount=excess,
                confidence="medium",
                group_key=year + ":" + estimate.currency,
                fields={"academic_year": year, "aid_total": aid_total, "cost_estimate": estimate.amount},
            )
        )
    return findings


def _academic_year(document: FinancialDocument) -> str:
    envelope = document.extraction_envelope or {}
    value = envelope.get("academic_year")
    if value:
        parsed = parse_terms(str(value))
        if parsed.academic_year:
            return f"{parsed.academic_year[0]}-{parsed.academic_year[1]}"
    term = document_term(document)
    if term.is_known and term.year:
        start = term.year if term.season == "fall" else term.year - 1
        return f"{start}-{start + 1}"
    return "unknown"
