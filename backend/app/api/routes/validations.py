from datetime import UTC, datetime
from uuid import uuid4

from fastapi import APIRouter, HTTPException, status

from app.db.repositories import get_report, list_reports, save_report
from app.schemas.documents import DocumentSummary, FinancialDocument
from app.schemas.validation import ValidationReport
from app.services.validation.engine import validate_documents

router = APIRouter(prefix="/validations", tags=["validations"])


@router.post("", response_model=ValidationReport, status_code=status.HTTP_201_CREATED)
def create_validation(documents: list[FinancialDocument]) -> ValidationReport:
    if len(documents) < 2:
        raise HTTPException(status_code=400, detail="Upload at least two documents to cross-check.")
    findings = validate_documents(documents)
    report = ValidationReport(
        id=str(uuid4()),
        created_at=datetime.now(UTC),
        documents=[
            DocumentSummary(
                id=doc.id,
                filename=doc.filename,
                document_type=doc.document_type,
                amount=doc.amount,
                currency=doc.currency,
                term=doc.term,
                deadline=doc.deadline,
                required_credits=doc.required_credits,
            )
            for doc in documents
        ],
        findings=findings,
        summary=(
            f"{len(findings)} potential {'inconsistency' if len(findings) == 1 else 'inconsistencies'} found."
            if findings
            else "No potential inconsistencies detected."
        ),
    )
    save_report(report)
    return report


@router.get("", response_model=list[ValidationReport])
def get_validations() -> list[ValidationReport]:
    return list_reports()


@router.get("/{report_id}", response_model=ValidationReport)
def get_validation(report_id: str) -> ValidationReport:
    report = get_report(report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Validation report not found.")
    return report
