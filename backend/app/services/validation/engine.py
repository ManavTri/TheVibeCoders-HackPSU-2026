import logging
import traceback
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from app.core.config import get_settings
from app.schemas.documents import FinancialDocument
from app.schemas.validation import Finding, Severity
from app.services.validation.ledger import build_ledger
from app.services.validation.rules.awards import (
    _amount_mismatches,
    _disbursement_splits,
    _duplicate_awards,
    _loan_offer_mismatches,
    _missing_on_bill,
    _unsupported_bill_credit,
)
from app.services.validation.rules.base import RuleContext, ValidationConfig
from app.services.validation.rules.coverage import (
    cost_of_attendance_findings,
    currency_findings,
    term_gap_findings,
    term_surplus_findings,
)
from app.services.validation.rules.eligibility import (
    award_conditions_findings,
    credit_requirement_findings,
)
from app.services.validation.rules.programs import (
    housing_comparison_findings,
    payment_plan_findings,
    program_aid_gap_findings,
    program_double_charge_findings,
)
from app.services.validation.rules.quality import quality_findings
from app.services.validation.rules.timing import (
    _deadline_status,
    _disbursement_after_due,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RuleDefinition:
    id: str
    check: Callable[[RuleContext], list[Finding]]


RULES: tuple[RuleDefinition, ...] = (
    RuleDefinition("coverage.term_gap", term_gap_findings),
    RuleDefinition("coverage.term_surplus", term_surplus_findings),
    RuleDefinition("award.missing_on_bill", _missing_on_bill),
    RuleDefinition("bill.unsupported_credit", _unsupported_bill_credit),
    RuleDefinition("award.amount_mismatch", _amount_mismatches),
    RuleDefinition("award.disbursement_split", _disbursement_splits),
    RuleDefinition("timing.disbursement_after_due", _disbursement_after_due),
    RuleDefinition("timing.deadline_status", _deadline_status),
    RuleDefinition("eligibility.credit_requirement", credit_requirement_findings),
    RuleDefinition("eligibility.credit_requirement", award_conditions_findings),
    RuleDefinition("duplicate.award", _duplicate_awards),
    RuleDefinition("coverage.over_cost_of_attendance", cost_of_attendance_findings),
    RuleDefinition("program.double_charge", program_double_charge_findings),
    RuleDefinition("program.aid_gap", program_aid_gap_findings),
    RuleDefinition("loan.offer_mismatch", _loan_offer_mismatches),
    RuleDefinition("plan.installment_total", payment_plan_findings),
    RuleDefinition("housing.contract_vs_bill", housing_comparison_findings),
    RuleDefinition("currency.mismatch", currency_findings),
    RuleDefinition("quality.data_gaps", quality_findings),
)

_SEVERITY_ORDER = {
    Severity.ERROR: 0,
    Severity.WARNING: 1,
    Severity.INFO: 2,
}
MAX_DEFAULT_FINDINGS = 20
MAX_DEFAULT_INFO_FINDINGS = 3


def _default_validation_config() -> ValidationConfig:
    settings = get_settings()
    return ValidationConfig(
        llm_enabled=settings.llm_enabled,
        rule_assist_enabled=settings.llm_enabled and settings.rule_assist_enabled,
    )


def validate_documents(
    documents: list[FinancialDocument],
    *,
    today: date | None = None,
    include_all: bool = False,
    config: ValidationConfig | None = None,
    rule_errors: list[dict[str, str]] | None = None,
) -> list[Finding]:
    return evaluate_findings(
        documents,
        today=today,
        include_all=include_all,
        config=config,
        rule_errors=rule_errors,
    )


def evaluate_findings(
    documents: list[FinancialDocument],
    *,
    today: date | None = None,
    include_all: bool = False,
    config: ValidationConfig | None = None,
    rule_errors: list[dict[str, str]] | None = None,
) -> list[Finding]:
    """Normalize, ledger, and evaluate documents without reading or writing persistence."""
    evaluation_date = today if today is not None else date(2000, 1, 1)
    rules_config = config or _default_validation_config()
    ledger = build_ledger(
        documents,
        today=evaluation_date,
        calendar=rules_config.calendar,
    )
    context = RuleContext(ledger, documents, evaluation_date, rules_config)
    findings: list[Finding] = []
    for rule in RULES:
        try:
            findings.extend(rule.check(context))
        except Exception as exc:
            if rules_config.strict:
                raise
            error_class = type(exc).__name__
            if rule_errors is not None:
                rule_errors.append({"rule_id": rule.id, "error_class": error_class})
            stack = "".join(
                f'  File "{frame.filename}", line {frame.lineno}, in {frame.name}\n'
                for frame in traceback.extract_tb(exc.__traceback__)
            )
            logger.error(
                "Validation rule %s skipped (%s)\n%s",
                rule.id,
                error_class,
                stack,
            )
    findings = _post_process(findings, evaluation_date, rules_config)
    if not include_all:
        info_count = 0
        limited: list[Finding] = []
        for finding in findings:
            if finding.severity is Severity.INFO:
                info_count += 1
                if info_count > MAX_DEFAULT_INFO_FINDINGS:
                    continue
            limited.append(finding)
        findings = limited[:MAX_DEFAULT_FINDINGS]
    return findings


def _post_process(
    findings: list[Finding], today: date, config: ValidationConfig
) -> list[Finding]:
    merged: dict[tuple[str, str | None, str], Finding] = {}
    for finding in findings:
        key = (
            finding.rule_id,
            finding.term,
            finding.group_key or finding.id,
        )
        existing = merged.get(key)
        if existing is None:
            merged[key] = finding
            continue
        evidence = {
            item.model_dump_json(): item
            for item in [*existing.evidence, *finding.evidence]
        }
        fields = {**existing.fields, **finding.fields}
        merged[key] = Finding(
            rule_id=finding.rule_id,
            severity=min(
                (existing.severity, finding.severity),
                key=lambda severity: _SEVERITY_ORDER[severity],
            ),
            category=finding.category or existing.category,
            title=existing.title,
            explanation=existing.explanation
            if existing.explanation == finding.explanation
            else f"{existing.explanation} {finding.explanation}",
            document_ids=sorted(set(existing.document_ids + finding.document_ids)),
            fields=fields,
            suggested_action=existing.suggested_action,
            evidence=list(evidence.values()),
            term=finding.term or existing.term,
            impact_amount=max(
                (value for value in (existing.impact_amount, finding.impact_amount) if value is not None),
                default=None,
            ),
            confidence=_higher_confidence(existing.confidence, finding.confidence),
            group_key=finding.group_key or existing.group_key,
            via=finding.via or existing.via,
        )
    processed = [_enforce_severity(item, today, config) for item in merged.values()]
    processed.sort(
        key=lambda finding: (
            _SEVERITY_ORDER[finding.severity],
            -(finding.impact_amount or Decimal(-1)),
            finding.fields.get("nearest_deadline", "9999-12-31"),
            finding.id,
        )
    )
    return processed


def _higher_confidence(first: str | None, second: str | None) -> str | None:
    order = {None: 0, "low": 1, "medium": 2, "high": 3}
    return max((first, second), key=lambda value: order[value])


def _enforce_severity(
    finding: Finding, today: date, config: ValidationConfig
) -> Finding:
    severity = finding.severity
    if finding.rule_id == "timing.deadline_status":
        due = finding.fields.get("deadline")
        if due:
            due_date = date.fromisoformat(str(due))
            days = (due_date - today).days
            severity = (
                Severity.ERROR
                if days < 0
                else Severity.WARNING
                if days <= config.near_deadline_warning_days
                else Severity.INFO
            )
    if finding.rule_id == "coverage.term_gap":
        due = finding.fields.get("payment_due_date")
        if due:
            severity = (
                Severity.ERROR
                if date.fromisoformat(str(due)) < today
                else Severity.WARNING
            )
        else:
            severity = Severity.WARNING
    if severity is finding.severity:
        return finding
    return finding.model_copy(update={"severity": severity, "id": ""})
