from collections import Counter, defaultdict
from datetime import date
from decimal import Decimal
from typing import Literal

from fastapi import APIRouter, Response

from app.api.deps import CurrentUser, current_user_id
from app.db.repositories import get_current_findings, get_current_ledger
from app.schemas.validation import Finding, Severity
from app.services.validation.engine import (
    MAX_DEFAULT_FINDINGS,
    MAX_DEFAULT_INFO_FINDINGS,
)

router = APIRouter(prefix="/findings", tags=["findings"])


@router.get("", response_model=list[Finding])
def current_findings(
    user: CurrentUser,
    response: Response,
    term: str | None = None,
    severity: Severity | None = None,
    category: str | None = None,
    include: Literal["default", "all"] = "default",
) -> list[Finding]:
    rule_errors: list[dict[str, str]] = []
    findings = get_current_findings(
        current_user_id(user),
        include_all=include == "all",
        today=date.today(),
        rule_errors=rule_errors,
    )
    if rule_errors:
        response.headers["X-Rules-Skipped"] = str(len(rule_errors))
    if term is not None:
        findings = [finding for finding in findings if finding.term == term]
    if severity is not None:
        findings = [finding for finding in findings if finding.severity is severity]
    if category is not None:
        findings = [finding for finding in findings if finding.category == category]
    return findings


@router.get("/report")
def findings_report(user: CurrentUser) -> dict:
    user_id = current_user_id(user)
    rule_errors: list[dict[str, str]] = []
    findings = get_current_findings(
        user_id,
        include_all=True,
        today=date.today(),
        rule_errors=rule_errors,
    )
    visible = _limit_info(findings)
    counts = Counter(finding.severity.value for finding in findings)
    at_risk: dict[str, Decimal] = defaultdict(Decimal)
    for finding in findings:
        if finding.severity is Severity.INFO or finding.impact_amount is None:
            continue
        currency = str(finding.fields.get("currency") or "unspecified")
        at_risk[currency] += finding.impact_amount
    deadlines = [
        str(finding.fields["nearest_deadline"])
        for finding in findings
        if finding.fields.get("nearest_deadline")
    ]
    ledger = get_current_ledger(user_id, today=date.today())
    per_term = []
    for term, currencies in ledger["terms"].items():
        per_term.append(
            {
                "term": term,
                "by_currency": {
                    currency: {
                        key: value
                        for key, value in totals.items()
                        if key
                        in {
                            "charges",
                            "aid",
                            "payments",
                            "net_balance",
                            "gap",
                            "surplus",
                        }
                    }
                    for currency, totals in currencies.items()
                },
            }
        )
    return {
        "findings": [finding.model_dump(mode="json") for finding in visible],
        "summary": {
            "counts_by_severity": {
                severity.value: counts.get(severity.value, 0) for severity in Severity
            },
            "total_at_risk_amount": {
                currency: str(amount.quantize(Decimal("0.01")))
                for currency, amount in sorted(at_risk.items())
            },
            "earliest_action_deadline": min(deadlines, default=None),
            "per_term_headlines": per_term,
            "rule_errors": rule_errors,
            "skipped_rules": len(rule_errors),
        },
    }


def _limit_info(findings: list[Finding]) -> list[Finding]:
    count = 0
    visible: list[Finding] = []
    for finding in findings:
        if finding.severity is Severity.INFO:
            count += 1
            if count > MAX_DEFAULT_INFO_FINDINGS:
                continue
        visible.append(finding)
    return visible[:MAX_DEFAULT_FINDINGS]
