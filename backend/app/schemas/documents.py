from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field, model_validator


class DocumentType(StrEnum):
    AWARD_LETTER = "award_letter"
    TUITION_BILL = "tuition_bill"
    STUDY_ABROAD_QUOTE = "study_abroad_quote"


class DocumentStatus(StrEnum):
    UPLOADED = "uploaded"
    EXTRACTED = "extracted"
    FAILED = "failed"


class FinancialDocument(BaseModel):
    id: str
    filename: str
    document_type: DocumentType
    amount: Decimal | None = Field(default=None, ge=0)
    currency: str = "USD"
    term: str | None = None
    deadline: date | None = None
    required_credits: int | None = Field(default=None, ge=0)
    extracted_text: str = Field(default="", exclude=True)


class DocumentRecord(FinancialDocument):
    user_id: str = Field(exclude=True)
    storage_path: str = Field(exclude=True)
    status: DocumentStatus
    created_at: datetime
    extraction_error: str | None = None
    archived_at: datetime | None = None
    deleted_at: datetime | None = None
    state: Literal["active", "archived", "deleted"] = "active"


class DocumentCorrection(BaseModel):
    amount: Decimal | None = Field(default=None, ge=0)
    currency: str = Field(default="USD", min_length=3, max_length=3, pattern=r"^[A-Z]{3}$")
    term: str | None = None
    deadline: date | None = None
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
    deadline: date | None
    required_credits: int | None
