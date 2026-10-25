from app.schemas.documents import FinancialDocument
from app.schemas.validation import Finding, Severity


def check_credit_requirements(documents: list[FinancialDocument]) -> list[Finding]:
    requirements = [doc for doc in documents if doc.required_credits is not None]
    if not requirements:
        return []
    distinct = {doc.required_credits for doc in requirements}
    if len(distinct) < 2:
        return []
    return [
        Finding(
            rule_id="credits.requirements_disagree",
            severity=Severity.WARNING,
            title="Credit requirements differ",
            explanation="Documents list different credit-hour requirements. Ask the award provider which enrollment level controls your eligibility.",
            document_ids=[doc.id for doc in requirements],
            fields={"requirements": ", ".join(str(value) for value in sorted(distinct) if value is not None)},
            suggested_action="Ask the award provider which enrollment level controls your eligibility.",
        )
    ]


class CreditRequirementRule:
    id = "credits.requirements_disagree"

    def check(self, docs: list[FinancialDocument]) -> list[Finding]:
        return check_credit_requirements(docs)
