import json
import re
import time
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Protocol

from google.genai.errors import APIError
from httpx import TimeoutException
from pydantic import ValidationError

from app.core.config import Settings, get_settings
from app.schemas.documents import (
    DeadlineItem,
    DocumentType,
    ExtractionEnvelope,
    FinancialDocument,
)
from app.services.extraction.client import (
    create_gemini_client,
    extract_text,
    generate_envelope,
)

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


@dataclass(frozen=True)
class ExtractionResult:
    document: FinancialDocument
    envelope: ExtractionEnvelope
    extraction_source: str
    type_detected: DocumentType
    type_confidence: float
    needs_review: bool


class ExtractionError(ValueError):
    pass


class DocumentExtractor(Protocol):
    def extract(
        self,
        *,
        document_id: str,
        filename: str,
        pdf_bytes: bytes,
        document_type_override: DocumentType | None = None,
    ) -> ExtractionResult: ...


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
    )


def _legacy_document(
    *, envelope: ExtractionEnvelope, document_id: str, filename: str, type_override: DocumentType | None
) -> FinancialDocument:
    due_dates = [
        item.date
        for item in envelope.deadlines
        if "due" in item.label.casefold() or "response" in item.label.casefold()
    ]
    return FinancialDocument(
        id=document_id,
        filename=filename,
        document_type=type_override or envelope.document_type,
        amount=envelope.total_amount,
        currency=envelope.currency or "USD",
        term=envelope.term,
        deadline=min(due_dates) if due_dates else None,
        required_credits=envelope.required_credits,
    )


def _result(
    envelope: ExtractionEnvelope,
    *,
    document_id: str,
    filename: str,
    document_type_override: DocumentType | None,
    source: str,
) -> ExtractionResult:
    return ExtractionResult(
        document=_legacy_document(
            envelope=envelope,
            document_id=document_id,
            filename=filename,
            type_override=document_type_override,
        ),
        envelope=envelope,
        extraction_source=source,
        type_detected=envelope.document_type,
        type_confidence=envelope.type_confidence,
        needs_review=envelope.type_confidence < 0.6,
    )


def _fallback_type(text: str) -> tuple[DocumentType, float]:
    value = text.casefold()
    if "study abroad" in value or "education abroad" in value:
        return DocumentType.STUDY_ABROAD_QUOTE, 0.5
    if "financial aid package" in value or "financial aid award" in value:
        return DocumentType.FINANCIAL_AID_PACKAGE, 0.5
    if "scholarship" in value or "award letter" in value:
        return DocumentType.AWARD_LETTER, 0.5
    if "tuition bill" in value or "student account statement" in value or "tuition invoice" in value:
        return DocumentType.TUITION_BILL, 0.5
    if "loan offer" in value or "student loan" in value:
        return DocumentType.LOAN_OFFER, 0.5
    if "payment plan" in value:
        return DocumentType.PAYMENT_PLAN, 0.5
    if "housing contract" in value or "residence hall" in value:
        return DocumentType.HOUSING_CONTRACT, 0.5
    return DocumentType.OTHER, 0.0


class FallbackExtractor:
    def extract(
        self,
        *,
        document_id: str,
        filename: str,
        pdf_bytes: bytes,
        document_type_override: DocumentType | None = None,
    ) -> ExtractionResult:
        text = extract_text(pdf_bytes)
        detected_type, confidence = _fallback_type(text)
        document = extract_document(
            document_id=document_id,
            filename=filename,
            document_type=detected_type,
            text=text,
        )
        due_date = document.deadline
        envelope = ExtractionEnvelope(
            document_type=detected_type,
            type_confidence=confidence,
            currency=document.currency,
            term=document.term,
            total_amount=document.amount,
            required_credits=document.required_credits,
            deadlines=[DeadlineItem(label="Payment due", date=due_date)] if due_date else [],
        )
        return _result(
            envelope,
            document_id=document_id,
            filename=filename,
            document_type_override=document_type_override,
            source="fallback",
        )


class GeminiExtractor:
    def __init__(
        self,
        settings: Settings | None = None,
        *,
        client: object | None = None,
        fallback: FallbackExtractor | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.client = client
        self.fallback = fallback or FallbackExtractor()

    def extract(
        self,
        *,
        document_id: str,
        filename: str,
        pdf_bytes: bytes,
        document_type_override: DocumentType | None = None,
    ) -> ExtractionResult:
        if not self.settings.llm_enabled or not self.settings.llm_model:
            return self.fallback.extract(
                document_id=document_id,
                filename=filename,
                pdf_bytes=pdf_bytes,
                document_type_override=document_type_override,
            )

        client = self.client or create_gemini_client(
            self.settings.llm_api_key or "", self.settings.llm_timeout_seconds
        )
        for attempt in range(2):
            try:
                response_text = generate_envelope(client, self.settings.llm_model, pdf_bytes)
                envelope = ExtractionEnvelope.model_validate(json.loads(response_text))
                if len(envelope.summary) > 300:
                    raise ValueError("Gemini summary exceeded the 300 character limit.")
                return _result(
                    envelope,
                    document_id=document_id,
                    filename=filename,
                    document_type_override=document_type_override,
                    source="gemini",
                )
            except (json.JSONDecodeError, ValidationError, ValueError) as exc:
                if attempt == 0 and _is_retryable(exc):
                    time.sleep(0.25)
                    continue
                break
            except (APIError, TimeoutError, TimeoutException) as exc:
                if attempt == 0 and _is_retryable(exc):
                    time.sleep(0.25)
                    continue
                break

        try:
            return self.fallback.extract(
                document_id=document_id,
                filename=filename,
                pdf_bytes=pdf_bytes,
                document_type_override=document_type_override,
            )
        except ValueError as exc:
            raise ExtractionError(str(exc)) from exc


def _is_retryable(error: Exception) -> bool:
    if isinstance(error, TimeoutError) or "timeout" in type(error).__name__.casefold():
        return True
    status = getattr(error, "status_code", None)
    if status is None:
        status = getattr(getattr(error, "response", None), "status_code", None)
    return status == 429 or isinstance(status, int) and 500 <= status < 600


def get_document_extractor() -> DocumentExtractor:
    settings = get_settings()
    if settings.llm_enabled and settings.llm_model:
        return GeminiExtractor(settings)
    return FallbackExtractor()
