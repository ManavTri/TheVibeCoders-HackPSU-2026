from app.schemas.validation import Finding, Severity
from app.services.validation.rules.base import RuleContext
from app.services.validation.rules.common import (
    build_finding,
    document_lines,
    document_term,
    evidence_for_document,
)


def quality_findings(context: RuleContext) -> list[Finding]:
    findings: list[Finding] = []
    for document in context.documents:
        missing: list[str] = []
        evidence = []
        term = document_term(document)
        if not term.is_known:
            missing.append("an explicit, parseable academic term")
            evidence.append(
                evidence_for_document(document, "term", "Academic term", document.term)
            )
        envelope = document.extraction_envelope or {}
        has_amount = (
            document.amount is not None
            or envelope.get("total_amount") is not None
            or any(item.amount is not None for item in document_lines(document))
        )
        if not has_amount:
            missing.append("an explicit amount or itemized financial value")
            evidence.append(
                evidence_for_document(document, "amount", "Document amount", None)
            )
        date_values = [
            item
            for key in ("deadlines", "payment_due_dates", "disbursements")
            for item in (envelope.get(key, []) if isinstance(envelope.get(key, []), list) else [])
        ]
        if not document.deadline and not any(
            isinstance(item, dict) and item.get("date") for item in date_values
        ):
            missing.append("a labeled date or disbursement date")
            evidence.append(
                evidence_for_document(document, "deadlines", "Document dates", None)
            )
        confidence = document.type_confidence
        if confidence is None:
            confidence = envelope.get("type_confidence")
        try:
            confidence_value = float(confidence) if confidence is not None else None
        except (TypeError, ValueError):
            confidence_value = 0.0
        if confidence_value is not None and confidence_value < 0.6:
            missing.append(f"higher-confidence document classification ({confidence})")
            evidence.append(
                evidence_for_document(
                    document,
                    "type_confidence",
                    "Document type confidence",
                    confidence,
                )
            )
        if not missing:
            continue
        skipped = (
            " Term-dependent comparisons are skipped for this document."
            if not term.is_known
            else ""
        )
        findings.append(
            build_finding(
                rule_id="quality.data_gaps",
                severity=Severity.INFO,
                category="data_quality",
                title=f"{document.filename} is missing {len(missing)} validation detail(s)",
                explanation=(
                    f"{document.filename} does not provide {', '.join(missing)}. "
                    "These gaps limit the checks that can be made from the uploaded set."
                    + skipped
                ),
                evidence=evidence,
                suggested_action=(
                    f"Check {document.filename} against the original statement and add or correct the missing "
                    "term, amount, or labeled date before relying on cross-document comparisons."
                ),
                document_ids=[document.id],
                term=str(term) if term.is_known else None,
                confidence="low",
                group_key=document.id,
                fields={"missing_details": missing, "term_analysis_skipped": not term.is_known},
            )
        )
    return findings
