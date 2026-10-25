from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from app.api.deps import CurrentUser, current_user_id
from app.db.repositories import (
    create_validation_run,
    get_document,
    get_validation_run,
    list_documents,
)
from app.schemas.documents import DocumentStatus, FinancialDocument
from app.schemas.validation import ValidationReport, ValidationRequest
from app.services.validation.evaluate import evaluate_findings

router = APIRouter(prefix="/validations", tags=["validations"])


@router.post("", response_model=ValidationReport, status_code=status.HTTP_201_CREATED)
def create_validation(
    user: CurrentUser,
    request: ValidationRequest | None = None,
) -> ValidationReport:
    request = request or ValidationRequest()
    user_id = current_user_id(user)
    if request.document_ids is None:
        records = list_documents(user_id, state="all")
    else:
        document_ids = [str(document_id) for document_id in request.document_ids]
        if len(set(document_ids)) != len(document_ids):
            raise HTTPException(status_code=400, detail="Document IDs must be unique.")
        records = []
        for document_id in document_ids:
            record = get_document(user_id, document_id)
            if record is None:
                raise HTTPException(status_code=404, detail="One or more documents were not found.")
            records.append(record)
    records = [record for record in records if record["status"] == DocumentStatus.EXTRACTED.value]
    if len(records) < 2:
        raise HTTPException(
            status_code=400,
            detail="At least two successfully extracted documents are required to validate.",
        )
    documents = [FinancialDocument.model_validate(record) for record in records]
    findings = evaluate_findings(documents)
    return create_validation_run(user_id, documents, findings)


@router.get("/{run_id}", response_model=ValidationReport)
def get_validation(run_id: UUID, user: CurrentUser) -> ValidationReport:
    report = get_validation_run(current_user_id(user), str(run_id))
    if report is None:
        raise HTTPException(status_code=404, detail="Validation report not found.")
    return report
