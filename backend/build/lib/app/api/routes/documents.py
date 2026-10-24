from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, File, Form, HTTPException, Response, UploadFile, status

from app.api.deps import CurrentUser, current_user_id
from app.core.config import get_settings
from app.db.repositories import (
    correct_document,
    create_document,
    delete_document,
    download_document,
    get_document,
    list_documents,
    update_document,
)
from app.schemas.documents import (
    DocumentCorrection,
    DocumentRecord,
    DocumentStatus,
    DocumentType,
    FinancialDocument,
)
from app.services.extraction.client import extract_text
from app.services.extraction.extractor import extract_document

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("", response_model=DocumentRecord, status_code=status.HTTP_201_CREATED)
async def upload_document(
    user: CurrentUser,
    file: Annotated[UploadFile, File()],
    document_type: Annotated[DocumentType, Form()],
) -> DocumentRecord:
    filename = file.filename or "statement.pdf"
    if file.content_type != "application/pdf" and not filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=415, detail="Only PDF documents are supported.")
    max_bytes = get_settings().max_upload_mb * 1024 * 1024
    content = await file.read(max_bytes + 1)
    if len(content) > max_bytes:
        raise HTTPException(status_code=413, detail=f"File exceeds the {get_settings().max_upload_mb} MB upload limit.")

    user_id = current_user_id(user)
    record = create_document(user_id, filename, document_type, content)
    try:
        text = extract_text(content)
        extracted = extract_document(
            document_id=record["id"],
            filename=filename,
            document_type=document_type,
            text=text,
        )
    except ValueError as exc:
        extracted = FinancialDocument(
            id=record["id"],
            filename=filename,
            document_type=document_type,
        )
        updated = update_document(
            user_id,
            record["id"],
            extracted,
            DocumentStatus.FAILED,
            extraction_error=str(exc),
        )
        if updated is None:
            raise RuntimeError("Uploaded document disappeared before extraction status could be saved.")
        return DocumentRecord.model_validate(updated)

    updated = update_document(user_id, record["id"], extracted, DocumentStatus.EXTRACTED)
    if updated is None:
        raise RuntimeError("Uploaded document disappeared before extraction results could be saved.")
    return DocumentRecord.model_validate(updated)


@router.get("", response_model=list[DocumentRecord])
def get_documents(user: CurrentUser) -> list[DocumentRecord]:
    return [DocumentRecord.model_validate(record) for record in list_documents(current_user_id(user))]


@router.get("/{document_id}", response_model=DocumentRecord)
def get_document_details(document_id: UUID, user: CurrentUser) -> DocumentRecord:
    record = get_document(current_user_id(user), str(document_id))
    if record is None:
        raise HTTPException(status_code=404, detail="Document not found.")
    return DocumentRecord.model_validate(record)


@router.patch("/{document_id}", response_model=DocumentRecord)
def patch_document(document_id: UUID, correction: DocumentCorrection, user: CurrentUser) -> DocumentRecord:
    updated = correct_document(current_user_id(user), str(document_id), correction.model_dump(exclude_unset=True))
    if updated is None:
        raise HTTPException(status_code=404, detail="Document not found.")
    return DocumentRecord.model_validate(updated)


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_document(document_id: UUID, user: CurrentUser) -> Response:
    if not delete_document(current_user_id(user), str(document_id)):
        raise HTTPException(status_code=404, detail="Document not found.")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{document_id}/file")
def get_document_file(document_id: UUID, user: CurrentUser) -> Response:
    content = download_document(current_user_id(user), str(document_id))
    if content is None:
        raise HTTPException(status_code=404, detail="Document not found.")
    return Response(content=content, media_type="application/pdf")
