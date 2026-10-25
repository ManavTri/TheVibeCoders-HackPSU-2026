import json
import logging
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
ENROLLED_CREDITS_PATTERN = re.compile(
    r"\benrolled\s+credits?\s*:\s*(\d{1,2})\b", re.IGNORECASE
)
REQUIRED_CREDITS_PATTERN = re.compile(
    r"\b(?:requires?|minimum(?:\s+of)?|at\s+least)\s*:?\s*(\d{1,2})\s+credits?\b",
    re.IGNORECASE,
)
TERM_PATTERN = re.compile(
    r"\b(Spring|Summer|Fall|Autumn|Winter)\s+(20\d{2})(?:\s+(?:semester|term))?\b",
    re.IGNORECASE,
)
TITLE_TYPE_PATTERNS = (
    (re.compile(r"\baward\s+letter\b", re.IGNORECASE), DocumentType.AWARD_LETTER),
    (re.compile(r"\bstatement\b", re.IGNORECASE), DocumentType.TUITION_BILL),
    (re.compile(r"\bquote\b", re.IGNORECASE), DocumentType.STUDY_ABROAD_QUOTE),
    (re.compile(r"\bagreement\b", re.IGNORECASE), DocumentType.HOUSING_CONTRACT),
    (re.compile(r"\boffer\b", re.IGNORECASE), DocumentType.LOAN_OFFER),
)

logger = logging.getLogger(__name__)
_startup_logged = False


@dataclass(frozen=True)
class ExtractionResult:
    document: FinancialDocument
    envelope: ExtractionEnvelope
    extraction_source: str
    type_detected: DocumentType
    type_confidence: float
    needs_review: bool
    extraction_fallback_reason: str | None = None


class ExtractionError(ValueError):
    def __init__(self, message: str, fallback_reason: str | None = None) -> None:
        super().__init__(message)
        self.fallback_reason = fallback_reason


class DocumentExtractor(Protocol):
    def extract(
        self,
        *,
        document_id: str,
        filename: str,
        pdf_bytes: bytes,
        document_type_hint: DocumentType | None = None,
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
    enrollment_match = ENROLLED_CREDITS_PATTERN.search(text)
    required_match = REQUIRED_CREDITS_PATTERN.search(text)
    return FinancialDocument(
        id=document_id,
        filename=filename,
        document_type=document_type,
        amount=amount,
        term=f"{term_match.group(1).title()} {term_match.group(2)}" if term_match else None,
        deadline=_date_match(text),
        required_credits=int(required_match.group(1)) if required_match else None,
        enrollment_credits=int(enrollment_match.group(1)) if enrollment_match else None,
    )


def _legacy_document(
    *,
    envelope: ExtractionEnvelope,
    document_id: str,
    filename: str,
) -> FinancialDocument:
    due_dates = [
        item.date
        for item in envelope.deadlines
        if "due" in item.label.casefold() or "response" in item.label.casefold()
    ]
    return FinancialDocument(
        id=document_id,
        filename=filename,
        document_type=envelope.document_type,
        amount=envelope.total_amount,
        currency=envelope.currency or "USD",
        term=envelope.term,
        deadline=min(due_dates) if due_dates else None,
        required_credits=envelope.required_credits,
        enrollment_credits=envelope.enrollment_credits,
    )


def _result(
    envelope: ExtractionEnvelope,
    *,
    document_id: str,
    filename: str,
    source: str,
    fallback_reason: str | None = None,
) -> ExtractionResult:
    return ExtractionResult(
        document=_legacy_document(
            envelope=envelope,
            document_id=document_id,
            filename=filename,
        ),
        envelope=envelope,
        extraction_source=source,
        type_detected=envelope.document_type,
        type_confidence=envelope.type_confidence,
        needs_review=envelope.type_confidence < 0.6,
        extraction_fallback_reason=fallback_reason,
    )


def _fallback_type(text: str) -> tuple[DocumentType, float]:
    title = next((line.strip() for line in text.splitlines() if line.strip()), "")
    for pattern, document_type in TITLE_TYPE_PATTERNS:
        if pattern.search(title):
            if document_type is DocumentType.HOUSING_CONTRACT and not any(
                word in text.casefold() for word in ("housing", "residence", "dorm")
            ):
                return DocumentType.OTHER, 0.75
            if document_type is DocumentType.LOAN_OFFER and not any(
                word in text.casefold() for word in ("loan", "financial aid", "student aid")
            ):
                return DocumentType.FINANCIAL_AID_PACKAGE, 0.75
            return document_type, 0.85
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
        document_type_hint: DocumentType | None = None,
        fallback_reason: str | None = None,
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
            term=document.term,
            total_amount=document.amount,
            required_credits=document.required_credits,
            enrollment_credits=document.enrollment_credits,
            deadlines=[DeadlineItem(label="Payment due", date=due_date)] if due_date else [],
        )
        return _result(
            envelope,
            document_id=document_id,
            filename=filename,
            source="fallback",
            fallback_reason=fallback_reason,
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
        document_type_hint: DocumentType | None = None,
    ) -> ExtractionResult:
        if not self.settings.llm_enabled:
            return self._fallback(
                "no_api_key",
                document_id=document_id,
                filename=filename,
                pdf_bytes=pdf_bytes,
                document_type_hint=document_type_hint,
            )
        if not self.settings.llm_model:
            return self._fallback(
                "no_model",
                document_id=document_id,
                filename=filename,
                pdf_bytes=pdf_bytes,
                document_type_hint=document_type_hint,
            )

        if self.client is None:
            self.client = create_gemini_client(
                self.settings.llm_api_key or "", self.settings.llm_timeout_seconds
            )
        client = self.client
        for attempt in range(2):
            try:
                response_text = generate_envelope(
                    client,
                    self.settings.llm_model,
                    pdf_bytes,
                    document_type_hint.value if document_type_hint else None,
                )
                envelope = ExtractionEnvelope.model_validate(json.loads(response_text))
                if len(envelope.summary) > 300:
                    raise ValueError("Gemini summary exceeded the 300 character limit.")
                return _result(
                    envelope,
                    document_id=document_id,
                    filename=filename,
                    source="gemini",
                )
            except (json.JSONDecodeError, ValidationError, ValueError) as exc:
                if attempt == 0 and _is_retryable(exc):
                    time.sleep(0.25)
                    continue
                return self._fallback(
                    "invalid_output",
                    error_class=type(exc).__name__,
                    document_id=document_id,
                    filename=filename,
                    pdf_bytes=pdf_bytes,
                    document_type_hint=document_type_hint,
                )
            except (APIError, TimeoutError, TimeoutException) as exc:
                if attempt == 0 and _is_retryable(exc):
                    time.sleep(0.25)
                    continue
                reason = "timeout" if isinstance(exc, (TimeoutError, TimeoutException)) else (
                    "rate_limited" if _status_code(exc) == 429 else "api_error"
                )
                return self._fallback(
                    reason,
                    error_class=type(exc).__name__,
                    document_id=document_id,
                    filename=filename,
                    pdf_bytes=pdf_bytes,
                    document_type_hint=document_type_hint,
                )
            except Exception as exc:  # noqa: BLE001 - SDK failures vary by transport and provider.
                return self._fallback(
                    "api_error",
                    error_class=type(exc).__name__,
                    document_id=document_id,
                    filename=filename,
                    pdf_bytes=pdf_bytes,
                    document_type_hint=document_type_hint,
                )

        return self._fallback(
            "api_error",
            document_id=document_id,
            filename=filename,
            pdf_bytes=pdf_bytes,
            document_type_hint=document_type_hint,
        )

    def _fallback(
        self,
        reason: str,
        *,
        error_class: str = "ConfigurationError",
        document_id: str,
        filename: str,
        pdf_bytes: bytes,
        document_type_hint: DocumentType | None,
    ) -> ExtractionResult:
        logger.warning(
            "Gemini extraction fallback reason=%s error_class=%s",
            reason,
            error_class,
        )
        try:
            return self.fallback.extract(
                document_id=document_id,
                filename=filename,
                pdf_bytes=pdf_bytes,
                document_type_hint=document_type_hint,
                fallback_reason=reason,
            )
        except ValueError as exc:
            raise ExtractionError(str(exc), fallback_reason=reason) from exc


def _is_retryable(error: Exception) -> bool:
    if isinstance(error, TimeoutError) or "timeout" in type(error).__name__.casefold():
        return True
    status = _status_code(error)
    return status == 429 or isinstance(status, int) and 500 <= status < 600


def _status_code(error: Exception) -> int | None:
    status = getattr(error, "status_code", None)
    if status is None:
        status = getattr(getattr(error, "response", None), "status_code", None)
    if status is None:
        status = getattr(error, "code", None)
    return status if isinstance(status, int) else None


def log_gemini_startup() -> None:
    global _startup_logged
    if _startup_logged:
        return
    settings = get_settings()
    logger.info(
        "Gemini extraction enabled=%s model=%s",
        settings.llm_enabled and bool(settings.llm_model),
        settings.llm_model or "<unset>",
    )
    _startup_logged = True


def get_document_extractor() -> DocumentExtractor:
    settings = get_settings()
    return GeminiExtractor(settings)
