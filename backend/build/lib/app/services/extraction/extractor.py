import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from app.schemas.documents import DocumentType, FinancialDocument

AMOUNT_PATTERN = re.compile(
    r"(?:award|scholarship|total|balance|tuition|program|amount|cost|fee)[^\n$]{0,35}"
    r"\$\s*([\d,]+(?:\.\d{1,2})?)",
    re.IGNORECASE,
)
DATE_PATTERN = re.compile(
    r"(?:deadline|due date|payment due|pay by)[^\n]{0,24}"
    r"((?:January|February|March|April|May|June|July|August|September|October|November|December)"
    r"\s+\d{1,2},?\s+\d{4}|\d{1,2}/\d{1,2}/\d{4})",
    re.IGNORECASE,
)
CREDIT_PATTERN = re.compile(r"(\d{1,2})\s+(?:minimum\s+)?credits?", re.IGNORECASE)
TERM_PATTERN = re.compile(
    r"\b(Spring|Summer|Fall|Autumn|Winter)\s+(20\d{2})(?:\s+(?:semester|term))?\b",
    re.IGNORECASE,
)


def _date_match(text: str) -> date | None:
    match = DATE_PATTERN.search(text)
    if not match:
        return None
    value = match.group(1).replace(",", "")
    for fmt in ("%B %d %Y", "%m/%d/%Y"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None


def extract_document(
    *, document_id: str, filename: str, document_type: DocumentType, text: str
) -> FinancialDocument:
    amount_match = AMOUNT_PATTERN.search(text)
    amount: Decimal | None = None
    if amount_match:
        try:
            amount = Decimal(amount_match.group(1).replace(",", ""))
        except InvalidOperation:
            amount = None

    term_match = TERM_PATTERN.search(text)
    credits_match = CREDIT_PATTERN.search(text)
    return FinancialDocument(
        id=document_id,
        filename=filename,
        document_type=document_type,
        amount=amount,
        term=f"{term_match.group(1).title()} {term_match.group(2)}" if term_match else None,
        deadline=_date_match(text),
        required_credits=int(credits_match.group(1)) if credits_match else None,
        extracted_text=text,
    )
