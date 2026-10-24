from app.schemas.documents import FinancialDocument
from app.schemas.validation import Finding
from app.services.validation.rules.amount_mismatch import check_amounts
from app.services.validation.rules.credit_requirement import check_credit_requirements
from app.services.validation.rules.deadline_conflict import check_deadlines
from app.services.validation.rules.term_mismatch import check_terms

RULES = (check_amounts, check_deadlines, check_terms, check_credit_requirements)


def validate_documents(documents: list[FinancialDocument]) -> list[Finding]:
    return [finding for rule in RULES for finding in rule(documents)]
