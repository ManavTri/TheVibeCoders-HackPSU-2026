from datetime import date
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class DocumentType(StrEnum):
    AWARD_LETTER = "award_letter"
    TUITION_BILL = "tuition_bill"
    STUDY_ABROAD_QUOTE = "study_abroad_quote"


class FinancialDocument(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    id: str
    filename: str
    document_type: DocumentType
    amount: Decimal | None = Field(default=None, ge=0)
    currency: str = "USD"
    term: str | None = None
    deadline: date | None = None
    required_credits: int | None = Field(default=None, ge=0)
    extracted_text: str = Field(default="", exclude=True)


class DocumentSummary(BaseModel):
    id: str
    filename: str
    document_type: DocumentType
    amount: Decimal | None
    currency: str
    term: str | None
    deadline: date | None
    required_credits: int | None
