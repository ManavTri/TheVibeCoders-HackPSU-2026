"""Text extraction adapter for uploaded PDF statements."""

from io import BytesIO

from pypdf import PdfReader
from pypdf.errors import PdfReadError


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
