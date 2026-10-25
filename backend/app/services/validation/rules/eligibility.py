from app.schemas.documents import FinancialDocument
from app.schemas.validation import Finding, Severity
from app.services.validation.normalize import assign_item_term, parse_terms
from app.services.validation.rules.base import RuleContext
from app.services.validation.rules.common import (
    build_finding,
    document_entries,
    document_lines,
    document_term,
    evidence_for_document,
)


def eligibility_findings(context: RuleContext) -> list[Finding]:
    return credit_requirement_findings(context) + award_conditions_findings(context)


def credit_requirement_findings(context: RuleContext) -> list[Finding]:
    findings: list[Finding] = []
    for award in context.documents:
        if award.document_type.value not in {"award_letter", "financial_aid_package"}:
            continue
        envelope = award.extraction_envelope or {}
        required = award.required_credits or envelope.get("required_credits")
        if required is None:
            continue
        try:
            required_credits = int(required)
        except (TypeError, ValueError):
            continue
        findings.extend(_credit_requirement_findings(context, award, required_credits))
    return findings


def award_conditions_findings(context: RuleContext) -> list[Finding]:
    return [
        finding
        for award in context.documents
        if award.document_type.value in {"award_letter", "financial_aid_package"}
        for finding in _conditions_finding(award, award.extraction_envelope or {})
    ]


def _credit_requirement_findings(
    context: RuleContext, award: FinancialDocument, required: int
) -> list[Finding]:
    award_entries = [
        entry
        for entry in document_entries(context.ledger, award.id)
        if entry.direction == "credit" and entry.term
    ]
    terms = sorted({entry.term for entry in award_entries if entry.term})
    if not terms:
        terms = [
            str(term)
            for term in parse_terms(award.term).terms
            if term.is_known
        ]
    if not terms:
        return []

    findings: list[Finding] = []
    observed_terms: set[str] = set()
    for term_value in terms:
        matching_award_entries = [
            entry for entry in award_entries if entry.term == term_value
        ]
        representative = next(
            (
                entry
                for entry in matching_award_entries
                if entry.kind == "scholarship"
            ),
            matching_award_entries[0] if matching_award_entries else None,
        )
        matched_bill = False
        for document in context.documents:
            if document.id == award.id:
                continue
            envelope = document.extraction_envelope or {}
            credits = envelope.get("enrollment_credits")
            if credits is None:
                continue
            document_terms = _document_term_values(document)
            if term_value not in document_terms:
                continue
            matched_bill = True
            observed_terms.add(term_value)
            try:
                enrolled = int(credits)
            except (TypeError, ValueError):
                continue
            if enrolled >= required:
                continue
            evidence = [
                evidence_for_document(
                    award, "required_credits", "Minimum required credits", required
                ),
                evidence_for_document(
                    document, "enrollment_credits", "Reported enrolled credits", enrolled
                ),
            ]
            if representative:
                evidence.append(
                    evidence_for_document(
                        award,
                        "line_items",
                        representative.label,
                        representative.amount,
                    )
                )
            findings.append(
                build_finding(
                    rule_id="eligibility.credit_requirement",
                    severity=Severity.ERROR,
                    category="eligibility",
                    title=f"{document.filename} reports {enrolled} credits, below the {required}-credit award requirement",
                    explanation=(
                        f"{award.filename} requires at least {required} credits for {term_value}; "
                        f"{document.filename} reports enrollment of {enrolled} credits. "
                        "This may affect award eligibility."
                    ),
                    evidence=evidence,
                    suggested_action=(
                        "Confirm your registered credit total with the registrar and ask the award provider whether "
                        f"{required} credits are required by the term's add/drop deadline."
                    ),
                    document_ids=[award.id, document.id],
                    term=term_value,
                    impact_amount=representative.amount if representative else None,
                    confidence="high",
                    group_key=f"{award.id}:{term_value}:{document.id}",
                    fields={
                        "required_credits": required,
                        "enrollment_credits": enrolled,
                    },
                )
            )
        if not matched_bill:
            findings.append(
                build_finding(
                    rule_id="eligibility.credit_requirement",
                    severity=Severity.INFO,
                    category="eligibility",
                    title=f"Verify the {required}-credit requirement for {term_value}",
                    explanation=(
                        f"{award.filename} requires at least {required} credits for {term_value}, "
                        "but no uploaded document states the student's enrolled credits."
                    ),
                    evidence=[
                        evidence_for_document(
                            award, "required_credits", "Minimum required credits", required
                        )
                    ],
                    suggested_action=(
                        "Check your registered credits with the registrar and confirm the minimum with the award provider "
                        f"before the {term_value} enrollment deadline."
                    ),
                    document_ids=[award.id],
                    term=term_value,
                    confidence="medium",
                    group_key=f"{award.id}:{term_value}:credits-unverified",
                    fields={"required_credits": required, "enrollment_credits": None},
                )
            )
    return findings


def _document_term_values(document: FinancialDocument) -> set[str]:
    envelope = document.extraction_envelope or {}
    values: set[str] = set()
    for line_item in document_lines(document):
        assignment = assign_item_term(
            item_term=line_item.term,
            document_term=document.term,
            document_terms=envelope.get("terms", []),
            item_date=line_item.date,
        )
        if assignment.term and assignment.term.is_known:
            values.add(str(assignment.term))
    if not values:
        values.update(
            str(term) for term in parse_terms(document.term).terms if term.is_known
        )
    return values


def _conditions_finding(
    award: FinancialDocument, envelope: dict
) -> list[Finding]:
    conditions = envelope_conditions(envelope)
    minimum_gpa = envelope.get("min_gpa")
    if minimum_gpa is None and not conditions:
        return []
    values = []
    if minimum_gpa is not None:
        values.append(f"minimum GPA {minimum_gpa}")
    values.extend(conditions)
    evidence = [
        evidence_for_document(award, "min_gpa", "Minimum GPA", minimum_gpa)
    ] if minimum_gpa is not None else []
    evidence.extend(
        evidence_for_document(award, "conditions", "Award condition", condition)
        for condition in conditions
    )
    term = document_term(award)
    term_value = str(term) if term.is_known else None
    return [
        build_finding(
            rule_id="eligibility.credit_requirement",
            severity=Severity.INFO,
            category="eligibility",
            title=f"Verify the conditions listed in {award.filename}",
            explanation=(
                f"{award.filename} lists {', '.join(values)}. The uploaded records do not establish whether "
                "these conditions are currently satisfied."
            ),
            evidence=evidence,
            suggested_action=(
                "Review these conditions with the award provider"
                + (f" for {term_value}." if term_value else ".")
            ),
            document_ids=[award.id],
            term=term_value,
            confidence="medium",
            group_key=award.id + ":conditions",
            fields={"conditions": values},
        )
    ]


def envelope_conditions(envelope: dict) -> list[str]:
    raw = envelope.get("conditions", [])
    return [str(value) for value in raw if isinstance(value, str) and value.strip()] if isinstance(raw, list) else []
