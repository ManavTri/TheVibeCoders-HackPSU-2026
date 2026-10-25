"""PDF text and Gemini client adapters."""

from io import BytesIO
from typing import Any

from pypdf import PdfReader
from pypdf.errors import PdfReadError


def create_gemini_client(api_key: str, timeout_seconds: int) -> Any:
    from google import genai
    from google.genai import types

    return genai.Client(
        api_key=api_key,
        http_options=types.HttpOptions(timeout=timeout_seconds * 1000),
    )


def generate_envelope(
    client: Any,
    model: str,
    pdf_bytes: bytes,
    document_type_hint: str | None = None,
) -> str:
    from google.genai import types

    from app.schemas.documents import ExtractionEnvelope
    from app.services.extraction.prompts import EXTRACTION_INSTRUCTIONS

    instructions = EXTRACTION_INSTRUCTIONS
    if document_type_hint:
        instructions += (
            "\nThe user optionally suggested this document category: "
            f"{document_type_hint}. Treat it only as a hint; classify the PDF "
            "from its contents and return the category that best matches the document."
        )

    response = client.models.generate_content(
        model=model,
        contents=[
            instructions,
            types.Part.from_bytes(data=pdf_bytes, mime_type="application/pdf"),
        ],
        config=types.GenerateContentConfig(
            temperature=0,
            response_mime_type="application/json",
            response_json_schema=ExtractionEnvelope.model_json_schema(),
        ),
    )
    if not response.text:
        raise ValueError("Gemini returned no structured extraction data.")
    return response.text


def extract_text(pdf_bytes: bytes) -> str:
    try:
        reader = PdfReader(BytesIO(pdf_bytes), strict=True)
        if reader.is_encrypted:
            raise ValueError("Encrypted PDFs are not supported. Export an unprotected copy and retry.")
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
    except (PdfReadError, ValueError, OSError) as exc:
        raise ValueError(f"Unable to read PDF: {exc}") from exc
    if not text.strip():
        raise ValueError("This PDF has no selectable text. OCR support is not enabled yet.")
    return text
