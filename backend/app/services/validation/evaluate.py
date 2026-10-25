from app.schemas.documents import FinancialDocument
from app.schemas.validation import Finding
from app.services.validation.engine import validate_documents


def evaluate_findings(documents: list[FinancialDocument]) -> list[Finding]:
    """Evaluate the supplied documents without reading or writing persistence."""
    return validate_documents(documents)
