from datetime import date as Date
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


class DocumentType(StrEnum):
    AWARD_LETTER = "award_letter"
    TUITION_BILL = "tuition_bill"
    FINANCIAL_AID_PACKAGE = "financial_aid_package"
    STUDY_ABROAD_QUOTE = "study_abroad_quote"
    LOAN_OFFER = "loan_offer"
    PAYMENT_PLAN = "payment_plan"
    HOUSING_CONTRACT = "housing_contract"
    OTHER = "other"


class DocumentStatus(StrEnum):
    UPLOADED = "uploaded"
    EXTRACTED = "extracted"
    FAILED = "failed"


def display_category(document_type: DocumentType | str) -> str:
    try:
        normalized_type = DocumentType(document_type)
    except ValueError:
        return "Uploaded"
    return {
        DocumentType.FINANCIAL_AID_PACKAGE: "Financial aid",
        DocumentType.TUITION_BILL: "Tuition",
        DocumentType.AWARD_LETTER: "Scholarship",
        DocumentType.STUDY_ABROAD_QUOTE: "Budget",
        DocumentType.LOAN_OFFER: "Financial aid",
        DocumentType.PAYMENT_PLAN: "Tuition",
        DocumentType.HOUSING_CONTRACT: "Budget",
    }.get(normalized_type, "Uploaded")


class DeadlineItem(BaseModel):
    label: str
    date: Date


class LineItem(BaseModel):
    label: str
    amount: Decimal
    category: str
    date: Date | None = None
    direction: Literal["charge", "credit", "unknown"] | None = None
    term: str | None = None
    kind: Literal[
        "tuition",
        "fees",
        "housing",
        "meals",
        "books",
        "travel",
        "program_fee",
        "insurance",
        "other_charge",
        "scholarship",
        "grant",
        "loan",
        "work_study",
        "waiver",
        "payment",
        "refund",
        "other",
    ] | None = None


class Disbursement(BaseModel):
    date: Date
    amount: Decimal
    term: str | None = None
    award_label: str | None = None


class PaymentDueDate(BaseModel):
    label: str
    date: Date
    term: str | None = None


class ExtractionEnvelope(BaseModel):
    document_type: DocumentType
    type_confidence: float = Field(ge=0, le=1)
    issuer: str | None = None
    currency: str | None = None
    term: str | None = None
    document_date: Date | None = None
    total_amount: Decimal | None = Field(default=None, ge=0)
    required_credits: int | None = Field(default=None, ge=0)
    min_gpa: Decimal | None = Field(default=None, ge=0)
    deadlines: list[DeadlineItem] = Field(default_factory=list)
    line_items: list[LineItem] = Field(default_factory=list)
    disbursements: list[Disbursement] = Field(default_factory=list)
    enrollment_credits: int | None = Field(default=None, ge=0)
    academic_year: str | None = None
    terms: list[str] = Field(default_factory=list)
    payment_due_dates: list[PaymentDueDate] = Field(default_factory=list)
    exchange_rate: Decimal | None = Field(default=None, gt=0)
    conditions: list[str] = Field(default_factory=list)
    summary: str = Field(default="", max_length=300)
    action_required: bool = False
    action_reason: str | None = None


class FinancialDocument(BaseModel):
    id: str
    filename: str
    document_type: DocumentType
    amount: Decimal | None = Field(default=None, ge=0)
    currency: str = "USD"
    term: str | None = None
    deadline: Date | None = None
    required_credits: int | None = Field(default=None, ge=0)
    extracted_text: str = Field(default="", exclude=True)
    extraction_envelope: dict[str, Any] | None = None
    type_confidence: float | None = None


class DocumentRecord(FinancialDocument):
    user_id: str = Field(exclude=True)
    storage_path: str = Field(exclude=True)
    status: DocumentStatus
    created_at: datetime
    extraction_error: str | None = None
    category: str = "Uploaded"
    extraction_source: Literal["gemini", "fallback"] | None = None
    type_detected: DocumentType | None = None
    needs_review: bool = False
    user_edited_fields: list[str] = Field(default_factory=list)
    archived_at: datetime | None = None
    deleted_at: datetime | None = None
    state: Literal["active", "archived", "deleted"] = "active"


class DocumentCorrection(BaseModel):
    amount: Decimal | None = Field(default=None, ge=0, allow_inf_nan=False)
    currency: str = Field(default="USD", min_length=3, max_length=3, pattern=r"^[A-Z]{3}$")
    term: str | None = None
    deadline: Date | None = None
    required_credits: int | None = Field(default=None, ge=0)
    document_type: DocumentType = DocumentType.AWARD_LETTER

    @model_validator(mode="after")
    def require_correction(self) -> "DocumentCorrection":
        if not self.model_fields_set:
            raise ValueError("Provide at least one field to correct.")
        return self


class DocumentSummary(BaseModel):
    id: str
    filename: str
    document_type: DocumentType
    amount: Decimal | None
    currency: str
    term: str | None
    deadline: Date | None
    required_credits: int | None
