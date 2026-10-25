from datetime import datetime
from enum import StrEnum
from hashlib import sha256
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from app.schemas.documents import DocumentSummary


class Severity(StrEnum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class Finding(BaseModel):
    id: str = ""
    rule_id: str
    severity: Severity
    title: str
    explanation: str
    document_ids: list[str]
    fields: dict[str, Any] = Field(default_factory=dict)
    suggested_action: str

    @model_validator(mode="after")
    def assign_deterministic_id(self) -> "Finding":
        if not self.id:
            identity = "\x1f".join(
                [self.rule_id, *sorted(self.document_ids), *sorted(self.fields)]
            )
            self.id = sha256(identity.encode("utf-8")).hexdigest()[:16]
        return self


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
