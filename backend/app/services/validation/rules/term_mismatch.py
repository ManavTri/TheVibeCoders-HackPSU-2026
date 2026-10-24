from app.schemas.documents import FinancialDocument
from app.schemas.validation import Finding, Severity


def check_terms(documents: list[FinancialDocument]) -> list[Finding]:
    dated_terms = [doc for doc in documents if doc.term]
    terms = {doc.term for doc in dated_terms}
    if len(terms) < 2:
        return []
    return [
        Finding(
            rule_id="term.documents_disagree",
            severity=Severity.HIGH,
            title="Academic terms do not match",
            message="The uploaded documents reference different academic terms. Confirm that the award applies to the bill or program shown.",
            document_ids=[doc.id for doc in dated_terms],
            details={"terms": ", ".join(sorted(terms))},
        )
    ]
