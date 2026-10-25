import hashlib
import logging
from time import perf_counter
from typing import Annotated, Any, Literal
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Response,
    UploadFile,
    status,
)

from app.api.deps import CurrentUser, current_user_id
from app.core.config import get_settings
from app.db.repositories import (
    DuplicateDocumentError,
    InvalidDocumentStateError,
    archive_document,
    correct_document,
    create_document,
    delete_document,
    download_document,
    find_document_by_hash,
    get_document,
    list_documents,
    restore_document,
    soft_delete_document,
    update_document,
)
from app.schemas.documents import (
    DocumentCorrection,
    DocumentRecord,
    DocumentStatus,
    DocumentType,
    FinancialDocument,
)
from app.services.extraction.extractor import (
    DocumentExtractor,
    ExtractionError,
    ExtractionResult,
    get_document_extractor,
)

router = APIRouter(prefix="/documents", tags=["documents"])
logger = logging.getLogger(__name__)


@router.post("", response_model=DocumentRecord, status_code=status.HTTP_201_CREATED)
async def upload_document(
    user: CurrentUser,
    file: Annotated[UploadFile, File()],
    extractor: Annotated[DocumentExtractor, Depends(get_document_extractor)],
    document_type: Annotated[DocumentType | None, Form()] = None,
) -> DocumentRecord:
    filename = file.filename or "statement.pdf"
    if file.content_type != "application/pdf" and not filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=415, detail="Only PDF documents are supported.")
    max_bytes = get_settings().max_upload_mb * 1024 * 1024
    content = await file.read(max_bytes + 1)
    if len(content) > max_bytes:
        raise HTTPException(status_code=413, detail=f"File exceeds the {get_settings().max_upload_mb} MB upload limit.")

    user_id = current_user_id(user)
    content_sha256 = hashlib.sha256(content).hexdigest()
    existing = find_document_by_hash(user_id, content_sha256)
    if existing:
        raise _duplicate_document_response(existing)
    try:
        record = create_document(user_id, filename, document_type, content, content_sha256)
    except DuplicateDocumentError as exc:
        raise _duplicate_document_response(exc.existing) from exc

    return _extract_and_save(
        user_id=user_id,
        record=record,
        filename=filename,
        pdf_bytes=content,
        extractor=extractor,
        document_type_override=document_type,
        preserve_user_edits=True,
    )


def _extract_and_save(
    *,
    user_id: str,
    record: dict[str, Any],
    filename: str,
    pdf_bytes: bytes,
    extractor: DocumentExtractor,
    document_type_override: DocumentType | None = None,
    preserve_user_edits: bool,
) -> DocumentRecord:
    started_at = perf_counter()
    document_id = record["id"]
    try:
        result = extractor.extract(
            document_id=document_id,
            filename=filename,
            pdf_bytes=pdf_bytes,
            document_type_override=document_type_override,
        )
    except (ExtractionError, ValueError) as exc:
        duration_ms = round((perf_counter() - started_at) * 1000)
        logger.warning(
            "Document extraction failed document_id=%s duration_ms=%d source=fallback error_class=%s",
            document_id,
            duration_ms,
            type(exc).__name__,
        )
        failed_document = FinancialDocument(
            id=document_id,
            filename=filename,
            document_type=document_type_override or DocumentType.OTHER,
        )
        updated = update_document(
            user_id,
            document_id,
            failed_document,
            DocumentStatus.FAILED,
            extraction_error=str(exc),
            extraction_metadata={"extraction_source": "fallback", "needs_review": True},
            preserve_user_edits=preserve_user_edits,
        )
        if updated is None:
            raise RuntimeError("Uploaded document disappeared before extraction status could be saved.")
        return DocumentRecord.model_validate(updated)

    duration_ms = round((perf_counter() - started_at) * 1000)
    logger.info(
        "Document extraction complete document_id=%s duration_ms=%d source=%s",
        document_id,
        duration_ms,
        result.extraction_source,
    )
    updated = update_document(
        user_id,
        document_id,
        result.document,
        DocumentStatus.EXTRACTED,
        extraction_metadata=_extraction_metadata(result),
        preserve_user_edits=preserve_user_edits,
    )
    if updated is None:
        raise RuntimeError("Uploaded document disappeared before extraction results could be saved.")
    return DocumentRecord.model_validate(updated)


def _extraction_metadata(result: ExtractionResult) -> dict[str, Any]:
    return {
        "envelope": result.envelope.model_dump(mode="json"),
        "extraction_source": result.extraction_source,
        "type_confidence": result.type_confidence,
        "type_detected": result.type_detected.value,
        "needs_review": result.needs_review,
    }


@router.get("", response_model=list[DocumentRecord])
def get_documents(
    user: CurrentUser, state: Literal["active", "archived", "deleted"] = "active"
) -> list[DocumentRecord]:
    return [
        DocumentRecord.model_validate(record)
        for record in list_documents(current_user_id(user), state=state)
    ]


@router.post("/{document_id}/archive", response_model=DocumentRecord)
def archive_document_route(document_id: UUID, user: CurrentUser) -> DocumentRecord:
    try:
        updated = archive_document(current_user_id(user), str(document_id))
    except InvalidDocumentStateError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if updated is None:
        raise HTTPException(status_code=404, detail="Document not found.")
    return DocumentRecord.model_validate(updated)


@router.post("/{document_id}/restore", response_model=DocumentRecord)
def restore_document_route(document_id: UUID, user: CurrentUser) -> DocumentRecord:
    updated = restore_document(current_user_id(user), str(document_id))
    if updated is None:
        raise HTTPException(status_code=404, detail="Document not found.")
    return DocumentRecord.model_validate(updated)


@router.post("/{document_id}/delete", response_model=DocumentRecord)
def soft_delete_document_route(document_id: UUID, user: CurrentUser) -> DocumentRecord:
    updated = soft_delete_document(current_user_id(user), str(document_id))
    if updated is None:
        raise HTTPException(status_code=404, detail="Document not found.")
    return DocumentRecord.model_validate(updated)


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


@router.post("/{document_id}/reextract", response_model=DocumentRecord)
def reextract_document(
    document_id: UUID,
    user: CurrentUser,
    extractor: Annotated[DocumentExtractor, Depends(get_document_extractor)],
) -> DocumentRecord:
    user_id = current_user_id(user)
    record = get_document(user_id, str(document_id))
    if record is None:
        raise HTTPException(status_code=404, detail="Document not found.")
    content = download_document(user_id, str(document_id))
    if content is None:
        raise HTTPException(status_code=404, detail="Document file not found.")
    return _extract_and_save(
        user_id=user_id,
        record=record,
        filename=record["filename"],
        pdf_bytes=content,
        extractor=extractor,
        preserve_user_edits=True,
    )


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


def _duplicate_document_response(existing: dict[str, Any]) -> HTTPException:
    state = existing["state"]
    message = f"This file was already uploaded as '{existing['filename']}' ({state})."
    return HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail={
            "code": "duplicate_document",
            "message": message,
            "existing": {
                "id": existing["id"],
                "filename": existing["filename"],
                "state": state,
            },
        },
    )
