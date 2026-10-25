from datetime import date

from app.schemas.documents import FinancialDocument
from app.schemas.validation import Finding
from app.services.validation.engine import validate_documents
from app.services.validation.rules.base import ValidationConfig


def evaluate_findings(
    documents: list[FinancialDocument],
    *,
    today: date | None = None,
    include_all: bool = False,
    config: ValidationConfig | None = None,
    rule_errors: list[dict[str, str]] | None = None,
) -> list[Finding]:
    """Evaluate the supplied documents without reading or writing persistence."""
    return validate_documents(
        documents,
        today=today,
        include_all=include_all,
        config=config,
        rule_errors=rule_errors,
    )
