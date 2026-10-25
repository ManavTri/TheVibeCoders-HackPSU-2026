import json
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from hashlib import sha256
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from app.schemas.documents import DocumentSummary


class Severity(StrEnum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class FindingEvidence(BaseModel):
    document_id: str
    filename: str
    field: str
    label: str
    value: Any = None


class Finding(BaseModel):
    id: str = ""
    rule_id: str
    severity: Severity
    title: str
    explanation: str
    document_ids: list[str]
    fields: dict[str, Any] = Field(default_factory=dict)
    suggested_action: str
    category: Literal[
        "amount",
        "timing",
        "eligibility",
        "duplicate",
        "coverage",
        "data_quality",
        "opportunity",
    ] | None = None
    term: str | None = None
    impact_amount: Decimal | None = None
    confidence: Literal["high", "medium", "low"] | None = None
    evidence: list[FindingEvidence] = Field(default_factory=list)
    group_key: str | None = None
    via: str | None = None

    @model_validator(mode="after")
    def assign_deterministic_id(self) -> "Finding":
        if not self.id:
            subject = self.group_key
            if subject is None:
                subject = json.dumps(self.fields, sort_keys=True, default=str)
            identity = "\x1f".join(
                [
                    self.rule_id,
                    self.term or "",
                    *sorted(self.document_ids),
                    subject,
                ]
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
