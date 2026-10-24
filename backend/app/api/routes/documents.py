from typing import Annotated

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status

from app.core.config import get_settings
from app.schemas.documents import DocumentType, FinancialDocument
from app.services.extraction.client import extract_text
from app.services.extraction.extractor import extract_document

router = APIRouter(prefix="/documents", tags=["documents"])
MAX_FILES = 10


@router.post("/extract", response_model=list[FinancialDocument], status_code=status.HTTP_200_OK)
async def extract_documents(
    files: Annotated[list[UploadFile], File()],
    document_types: Annotated[list[DocumentType], Form()],
) -> list[FinancialDocument]:
    if not files or len(files) > MAX_FILES:
        raise HTTPException(status_code=400, detail=f"Upload between 1 and {MAX_FILES} PDF files.")
    if len(files) != len(document_types):
        raise HTTPException(status_code=400, detail="Provide one document type for each uploaded PDF.")

    settings = get_settings()
    extracted: list[FinancialDocument] = []
    for upload, document_type in zip(files, document_types, strict=True):
        if upload.content_type != "application/pdf" and not (upload.filename or "").lower().endswith(".pdf"):
            raise HTTPException(status_code=415, detail=f"{upload.filename or 'File'} is not a PDF.")
        content = await upload.read(settings.max_upload_mb * 1024 * 1024 + 1)
        if len(content) > settings.max_upload_mb * 1024 * 1024:
            raise HTTPException(status_code=413, detail=f"{upload.filename} exceeds the {settings.max_upload_mb} MB upload limit.")
        try:
            text = extract_text(content)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=f"{upload.filename}: {exc}") from exc
        extracted.append(
            extract_document(
                document_id=f"doc-{len(extracted) + 1}",
                filename=upload.filename or "statement.pdf",
                document_type=document_type,
                text=text,
            )
        )
    return extracted
