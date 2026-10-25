from collections import defaultdict
from datetime import date
from decimal import Decimal

from app.schemas.documents import DocumentType
from app.schemas.validation import Finding, Severity
from app.services.validation.normalize import assign_item_term, parse_term
from app.services.validation.rules.base import RuleContext
from app.services.validation.rules.common import (
    build_finding,
    deadline_records,
    evidence_for_document,
    format_money,
    term_matches,
)


def timing_findings(context: RuleContext) -> list[Finding]:
    return _deadline_status(context) + _disbursement_after_due(context)


def _deadline_status(context: RuleContext) -> list[Finding]:
    deduplicated: dict[tuple[str, date], list] = defaultdict(list)
    for document, label, due_date, term in deadline_records(context.documents):
        if _is_payment_due_date(document, due_date):
            balance = _term_balance(context, term, document.currency)
            if balance is None or balance.net_balance <= context.config.money_tolerance:
                continue
        deduplicated[(label.casefold(), due_date)].append((document, label, term))
    findings: list[Finding] = []
    for (normalized_label, due_date), records in deduplicated.items():
        days = (due_date - context.today).days
        if days > context.config.near_deadline_info_days:
            continue
        if days < 0:
            severity = Severity.ERROR
            status = f"was overdue by {-days} day(s) as of {context.today.isoformat()}"
        elif days <= context.config.near_deadline_warning_days:
            severity = Severity.WARNING
            status = f"is due in {days} day(s)"
        else:
            severity = Severity.INFO
            status = f"is due in {days} day(s)"
        payment_records = [
            document
            for document, _, _ in records
            if _is_payment_due_date(document, due_date)
        ]
        if payment_records:
            expected_aid = max(
                (
                    _term_balance(context, term, document.currency).expected_not_yet_billed
                    for document, _, term in records
                    if _is_payment_due_date(document, due_date)
                    and _term_balance(context, term, document.currency) is not None
                ),
                key=lambda entries: sum((entry.amount for entry in entries), Decimal(0)),
                default=[],
            )
            if expected_aid:
                term_balance = next(
                    (
                        _term_balance(context, term, document.currency)
                        for document, _, term in records
                        if _is_payment_due_date(document, due_date)
                        and _term_balance(context, term, document.currency) is not None
                    ),
                    None,
                )
                expected_total = sum((entry.amount for entry in expected_aid), Decimal(0))
                if term_balance and expected_total >= term_balance.net_balance:
                    severity = {
                        Severity.ERROR: Severity.WARNING,
                        Severity.WARNING: Severity.INFO,
                        Severity.INFO: Severity.INFO,
                    }[severity]
        display_label = records[0][1]
        term = next((record[2] for record in records if record[2]), None)
        evidence = [
            evidence_for_document(document, "deadlines", label, due_date.isoformat())
            for document, label, _ in records
        ]
        files = ", ".join(sorted({document.filename for document, _, _ in records}))
        findings.append(
            build_finding(
                rule_id="timing.deadline_status",
                severity=severity,
                category="timing",
                title=f"{display_label} on {due_date.isoformat()} {status}",
                explanation=(
                    f"{files} lists a {display_label.casefold()} deadline of {due_date.isoformat()}, which "
                    f"{status}. Missing this labeled deadline may affect payment, enrollment, or award eligibility."
                ),
                evidence=evidence,
                suggested_action=(
                    f"Check the issuer's instructions and complete or confirm the action for {display_label.casefold()} "
                    f"by {due_date.isoformat()}."
                ),
                document_ids=[document.id for document, _, _ in records],
                term=term,
                confidence="high",
                group_key=f"{normalized_label}:{due_date.isoformat()}",
                fields={"label": display_label, "deadline": due_date.isoformat()},
                nearest_deadline=due_date,
            )
        )
    return findings


def _is_payment_due_date(document, due_date: date) -> bool:
    for item in (document.extraction_envelope or {}).get("payment_due_dates", []):
        if not isinstance(item, dict) or not item.get("date"):
            continue
        try:
            if date.fromisoformat(str(item["date"])) == due_date:
                return True
        except ValueError:
            continue
    return False


def _term_balance(context: RuleContext, term_value: str | None, currency: str):
    term = parse_term(term_value)
    if not term.is_known:
        return None
    return context.ledger.terms.get(str(term), {}).get(currency)


def _disbursement_after_due(context: RuleContext) -> list[Finding]:
    findings: list[Finding] = []
    bills = [doc for doc in context.documents if doc.document_type == DocumentType.TUITION_BILL]
    for award in context.documents:
        if award.document_type not in {
            DocumentType.AWARD_LETTER,
            DocumentType.FINANCIAL_AID_PACKAGE,
            DocumentType.LOAN_OFFER,
        }:
            continue
        raw_disbursements = (award.extraction_envelope or {}).get("disbursements", [])
        if not isinstance(raw_disbursements, list):
            continue
        for disbursement in raw_disbursements:
            if not isinstance(disbursement, dict) or not disbursement.get("date"):
                continue
            try:
                disbursement_date = date.fromisoformat(str(disbursement["date"]))
            except ValueError:
                continue
            assignment = assign_item_term(
                item_term=disbursement.get("term"),
                document_term=award.term,
                document_terms=(award.extraction_envelope or {}).get("terms", []),
                item_date=disbursement_date,
                calendar=context.config.calendar,
            )
            if not assignment.term or not assignment.term.is_known:
                continue
            for bill in bills:
                due_dates = [
                    (document, label, due_date)
                    for document, label, due_date, due_term in deadline_records([bill])
                    if due_term and term_matches(str(assignment.term), due_term)
                    and any(token in label.casefold() for token in ("payment", "due"))
                ]
                for due_document, label, due_date in due_dates:
                    if disbursement_date <= due_date:
                        continue
                    days_late = (disbursement_date - due_date).days
                    amount = disbursement.get("amount")
                    currency = str((award.extraction_envelope or {}).get("currency") or award.currency)
                    amount_decimal = Decimal(str(amount)) if amount is not None else None
                    amount_text = (
                        format_money(amount_decimal, currency)
                        if amount_decimal is not None
                        else "an unstated amount"
                    )
                    findings.append(
                        build_finding(
                            rule_id="timing.disbursement_after_due",
                            severity=Severity.WARNING,
                            category="timing",
                            title=f"{award.filename} disburses {amount_text} {days_late} days after the {assignment.term} payment deadline",
                            explanation=(
                                f"{award.filename} lists the disbursement on {disbursement_date.isoformat()}, "
                                f"after {due_document.filename} lists {label.casefold()} on {due_date.isoformat()} "
                                f"for {assignment.term}. This timing may leave a balance due before aid arrives."
                            ),
                            evidence=[
                                evidence_for_document(
                                    award,
                                    "disbursements",
                                    str(disbursement.get("award_label") or "Disbursement"),
                                    {"amount": amount, "date": disbursement_date.isoformat()},
                                ),
                                evidence_for_document(
                                    due_document,
                                    "payment_due_dates",
                                    label,
                                    due_date.isoformat(),
                                ),
                            ],
                            suggested_action=(
                                f"Ask the billing office whether a payment deferral is available for {assignment.term} "
                                f"before {due_date.isoformat()}."
                            ),
                            document_ids=[award.id, due_document.id],
                            term=str(assignment.term),
                            impact_amount=amount_decimal,
                            confidence="high",
                            group_key=f"{assignment.term}:{disbursement_date}:{due_date}",
                            fields={
                                "disbursement_date": disbursement_date.isoformat(),
                                "payment_due_date": due_date.isoformat(),
                                "days_late": days_late,
                            },
                            nearest_deadline=due_date,
                        )
                    )
    return findings
