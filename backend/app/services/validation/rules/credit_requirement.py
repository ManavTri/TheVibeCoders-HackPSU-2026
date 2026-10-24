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
            severity=Severity.MEDIUM,
            title="Credit requirements differ",
            message="Documents list different credit-hour requirements. Ask the award provider which enrollment level controls your eligibility.",
            document_ids=[doc.id for doc in requirements],
            details={"requirements": ", ".join(str(value) for value in sorted(distinct) if value is not None)},
        )
    ]
