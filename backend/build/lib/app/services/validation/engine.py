from app.schemas.documents import FinancialDocument
from app.schemas.validation import Finding
from app.services.validation.rules.amount_mismatch import AmountMismatchRule
from app.services.validation.rules.base import Rule
from app.services.validation.rules.credit_requirement import CreditRequirementRule
from app.services.validation.rules.deadline_conflict import DeadlineConflictRule
from app.services.validation.rules.term_mismatch import TermMismatchRule

RULES: tuple[Rule, ...] = (
    AmountMismatchRule(),
    DeadlineConflictRule(),
    TermMismatchRule(),
    CreditRequirementRule(),
)


def validate_documents(documents: list[FinancialDocument]) -> list[Finding]:
    return [finding for rule in RULES for finding in rule.check(documents)]
