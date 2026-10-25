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
            severity=Severity.ERROR,
            title="Academic terms do not match",
            explanation="The uploaded documents reference different academic terms. Confirm that the award applies to the bill or program shown.",
            document_ids=[doc.id for doc in dated_terms],
            fields={"terms": ", ".join(sorted(terms))},
            suggested_action="Contact the award provider to confirm that the award applies to the term on the bill or program quote.",
        )
    ]


class TermMismatchRule:
    id = "term.documents_disagree"

    def check(self, docs: list[FinancialDocument]) -> list[Finding]:
        return check_terms(docs)
