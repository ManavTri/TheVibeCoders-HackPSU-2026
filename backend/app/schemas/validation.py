from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, Field

from app.schemas.documents import DocumentSummary


class Severity(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class Finding(BaseModel):
    rule_id: str
    severity: Severity
    title: str
    message: str
    document_ids: list[str]
    details: dict[str, str | Decimal | int | None] = Field(default_factory=dict)


class ValidationReport(BaseModel):
    id: str
    created_at: datetime
    documents: list[DocumentSummary]
    findings: list[Finding]
    summary: str
