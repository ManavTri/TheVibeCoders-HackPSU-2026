from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.documents import DocumentSummary


class Severity(StrEnum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class Finding(BaseModel):
    rule_id: str
    severity: Severity
    title: str
    explanation: str
    document_ids: list[str]
    fields: dict[str, Any] = Field(default_factory=dict)
    suggested_action: str


class ValidationReport(BaseModel):
    id: str
    created_at: datetime
    documents: list[DocumentSummary]
    findings: list[Finding]
    summary: str


class ValidationRequest(BaseModel):
    document_ids: list[UUID] | None = None


class InsightsRequest(BaseModel):
    run_id: UUID
