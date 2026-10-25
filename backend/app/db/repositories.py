"""The only module allowed to access Supabase Postgres or Storage."""

from datetime import UTC, date, datetime
from decimal import Decimal
from threading import RLock
from typing import Any
from uuid import uuid4

from app.core.config import get_settings
from app.db.supabase import Client, get_supabase_client
from app.schemas.documents import (
    DocumentStatus,
    DocumentType,
    FinancialDocument,
    display_category,
)
from app.schemas.validation import Finding, ValidationReport

_documents: dict[str, dict[str, Any]] = {}
_document_files: dict[str, bytes] = {}
_runs: dict[str, ValidationReport] = {}
_memory_lock = RLock()


class DuplicateDocumentError(Exception):
    def __init__(self, existing: dict[str, Any]):
        self.existing = existing
        super().__init__("This file has already been uploaded.")


class InvalidDocumentStateError(Exception):
    pass


def _document_state(row: dict[str, Any]) -> str:
    if row.get("deleted_at") is not None:
        return "deleted"
    if row.get("archived_at") is not None:
        return "archived"
    return "active"


def _client() -> Client | None:
    return get_supabase_client()


def _first(response: Any) -> dict[str, Any] | None:
    rows = response.data
    return rows[0] if rows else None


def _document_fields(document: FinancialDocument) -> dict[str, Any]:
    return {
        "amount": str(document.amount) if document.amount is not None else None,
        "currency": document.currency,
        "term": document.term,
        "deadline": document.deadline.isoformat() if document.deadline else None,
        "required_credits": document.required_credits,
        "document_type": document.document_type.value,
    }


def _record(row: dict[str, Any]) -> dict[str, Any]:
    extracted = row.get("extracted_json") or {}
    document_type = extracted.get("document_type", row["type"])
    return {
        "id": row["id"],
        "user_id": row["user_id"],
        "filename": row["filename"],
        "document_type": document_type,
        "category": display_category(document_type),
        "amount": extracted.get("amount"),
        "currency": extracted.get("currency", "USD"),
        "term": extracted.get("term"),
        "deadline": extracted.get("deadline"),
        "required_credits": extracted.get("required_credits"),
        "storage_path": row["storage_path"],
        "status": row["status"],
        "created_at": row["created_at"],
        "extraction_error": extracted.get("extraction_error"),
        "extraction_source": extracted.get("extraction_source"),
        "type_confidence": extracted.get("type_confidence"),
        "type_detected": extracted.get("type_detected"),
        "needs_review": extracted.get("needs_review", False),
        "user_edited_fields": extracted.get("user_edited_fields", []),
        "extraction_envelope": extracted.get("envelope"),
        "archived_at": row.get("archived_at"),
        "deleted_at": row.get("deleted_at"),
        "state": _document_state(row),
        "extracted_text": "",
    }


def _finding_from_row(row: dict[str, Any]) -> Finding:
    details = row.get("details")
    return Finding.model_validate(
        {
            "rule_id": row["rule_id"],
            "severity": row["severity"],
            "title": row["title"],
            "explanation": row["explanation"],
            "document_ids": row["document_ids"],
            "fields": row.get("fields") or {},
            "suggested_action": row["suggested_action"],
            **(details if isinstance(details, dict) else {}),
        }
    )


def find_document_by_hash(user_id: str, content_sha256: str) -> dict[str, Any] | None:
    client = _client()
    if client is None:
        with _memory_lock:
            row = next(
                (
                    row
                    for row in _documents.values()
                    if row["user_id"] == user_id and row.get("content_sha256") == content_sha256
                ),
                None,
            )
        return _record(row) if row else None
    response = (
        client.table("documents")
        .select("*")
        .eq("user_id", user_id)
        .eq("content_sha256", content_sha256)
        .limit(1)
        .execute()
    )
    row = _first(response)
    return _record(row) if row else None


def create_document(
    user_id: str,
    filename: str,
    document_type: DocumentType | None,
    content: bytes,
    content_sha256: str,
) -> dict[str, Any]:
    document_id = str(uuid4())
    storage_path = f"{user_id}/{document_id}.pdf"
    initial_type = document_type or DocumentType.OTHER
    edited_fields = ["document_type"] if document_type else []
    settings = get_settings()
    client = _client()
    if client is None:
        with _memory_lock:
            existing = next(
                (
                    row
                    for row in _documents.values()
                    if row["user_id"] == user_id and row.get("content_sha256") == content_sha256
                ),
                None,
            )
            if existing:
                raise DuplicateDocumentError(_record(existing))
            row = {
                "id": document_id,
                "user_id": user_id,
                "filename": filename,
                "type": initial_type.value,
                "storage_path": storage_path,
                "status": DocumentStatus.UPLOADED.value,
                "extracted_json": {
                    "document_type": initial_type.value,
                    "user_edited_fields": edited_fields,
                },
                "content_sha256": content_sha256,
                "archived_at": None,
                "deleted_at": None,
                "created_at": datetime.now(UTC).isoformat(),
            }
            _documents[document_id] = row
            _document_files[document_id] = content
        return _record(row)

    existing = find_document_by_hash(user_id, content_sha256)
    if existing:
        raise DuplicateDocumentError(existing)
    bucket = client.storage.from_(settings.supabase_storage_bucket)
    bucket.upload(storage_path, content, {"content-type": "application/pdf", "upsert": "false"})
    try:
        response = (
            client.table("documents")
            .insert(
                {
                    "id": document_id,
                    "user_id": user_id,
                    "type": initial_type.value,
                    "filename": filename,
                    "storage_path": storage_path,
                    "status": DocumentStatus.UPLOADED.value,
                    "extracted_json": {
                        "document_type": initial_type.value,
                        "user_edited_fields": edited_fields,
                    },
                    "content_sha256": content_sha256,
                }
            )
            .select("*")
            .execute()
        )
    except Exception as exc:
        bucket.remove([storage_path])
        if getattr(exc, "code", None) == "23505":
            existing = find_document_by_hash(user_id, content_sha256)
            if existing:
                raise DuplicateDocumentError(existing) from exc
        raise
    row = _first(response)
    if row is None:
        bucket.remove([storage_path])
        raise RuntimeError("Supabase did not return the newly inserted document.")
    return _record(row)


def get_document(user_id: str, document_id: str) -> dict[str, Any] | None:
    client = _client()
    if client is None:
        row = _documents.get(document_id)
        return _record(row) if row and row["user_id"] == user_id else None
    response = (
        client.table("documents")
        .select("*")
        .eq("id", document_id)
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )
    row = _first(response)
    return _record(row) if row else None


def list_documents(user_id: str, state: str = "active") -> list[dict[str, Any]]:
    client = _client()
    if client is None:
        with _memory_lock:
            rows = [
                row
                for row in _documents.values()
                if row["user_id"] == user_id
                and (state == "all" or _document_state(row) == state)
            ]
            return [
                _record(row)
                for row in sorted(rows, key=lambda item: item["created_at"], reverse=True)
            ]
    response = (
        client.table("documents")
        .select("*")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .execute()
    )
    return [
        _record(row)
        for row in response.data
        if state == "all" or _document_state(row) == state
    ]


def archive_document(user_id: str, document_id: str) -> dict[str, Any] | None:
    client = _client()
    if client is None:
        with _memory_lock:
            row = _documents.get(document_id)
            if row is None or row["user_id"] != user_id:
                return None
            if row.get("deleted_at") is not None:
                raise InvalidDocumentStateError("Deleted documents cannot be archived.")
            if row.get("archived_at") is None:
                row["archived_at"] = datetime.now(UTC).isoformat()
            return _record(row)
    existing = get_document(user_id, document_id)
    if existing is None:
        return None
    if existing["state"] == "deleted":
        raise InvalidDocumentStateError("Deleted documents cannot be archived.")
    if existing["state"] == "archived":
        return existing
    response = (
        client.table("documents")
        .update({"archived_at": datetime.now(UTC).isoformat()})
        .eq("id", document_id)
        .eq("user_id", user_id)
        .is_("deleted_at", "null")
        .select("*")
        .execute()
    )
    row = _first(response)
    return _record(row) if row else None


def restore_document(user_id: str, document_id: str) -> dict[str, Any] | None:
    client = _client()
    if client is None:
        with _memory_lock:
            row = _documents.get(document_id)
            if row is None or row["user_id"] != user_id:
                return None
            row["archived_at"] = None
            row["deleted_at"] = None
            return _record(row)
    response = (
        client.table("documents")
        .update({"archived_at": None, "deleted_at": None})
        .eq("id", document_id)
        .eq("user_id", user_id)
        .select("*")
        .execute()
    )
    row = _first(response)
    return _record(row) if row else None


def soft_delete_document(user_id: str, document_id: str) -> dict[str, Any] | None:
    client = _client()
    if client is None:
        with _memory_lock:
            row = _documents.get(document_id)
            if row is None or row["user_id"] != user_id:
                return None
            if row.get("deleted_at") is None:
                row["deleted_at"] = datetime.now(UTC).isoformat()
            return _record(row)
    existing = get_document(user_id, document_id)
    if existing is None:
        return None
    if existing["state"] == "deleted":
        return existing
    response = (
        client.table("documents")
        .update({"deleted_at": datetime.now(UTC).isoformat()})
        .eq("id", document_id)
        .eq("user_id", user_id)
        .select("*")
        .execute()
    )
    row = _first(response)
    return _record(row) if row else None


def _active_validation_documents(user_id: str) -> list[FinancialDocument]:
    records = [
        record
        for record in list_documents(user_id, state="active")
        if record["status"] == DocumentStatus.EXTRACTED.value
    ]
    return [FinancialDocument.model_validate(record) for record in records]


def get_current_findings(
    user_id: str,
    *,
    include_all: bool = False,
    today: date | None = None,
    rule_errors: list[dict[str, str]] | None = None,
) -> list[Finding]:
    from app.services.validation.evaluate import evaluate_findings

    documents = _active_validation_documents(user_id)
    if len(documents) < 2:
        return []
    return evaluate_findings(
        documents,
        today=today or date.today(),
        include_all=include_all,
        rule_errors=rule_errors,
    )


def get_current_ledger(user_id: str, *, today: date | None = None) -> dict[str, Any]:
    from app.services.validation.ledger import build_ledger

    ledger = build_ledger(_active_validation_documents(user_id), today=today or date.today())
    return ledger.as_dict()


def update_document(
    user_id: str,
    document_id: str,
    extracted: FinancialDocument,
    status: DocumentStatus,
    extraction_error: str | None = None,
    extraction_metadata: dict[str, Any] | None = None,
    preserve_user_edits: bool = False,
) -> dict[str, Any] | None:
    existing = get_document(user_id, document_id)
    if existing is None:
        return None

    previous_extracted = FinancialDocument.model_validate(existing)
    extracted_json = _document_fields(extracted)
    edited_fields = list(existing.get("user_edited_fields", []))
    if preserve_user_edits:
        previous_fields = _document_fields(previous_extracted)
        for field_name in edited_fields:
            if field_name in previous_fields:
                extracted_json[field_name] = previous_fields[field_name]

    metadata = extraction_metadata or {}
    extracted_json.update(
        {
            "envelope": metadata.get("envelope", existing.get("extraction_envelope")),
            "extraction_source": metadata.get(
                "extraction_source", existing.get("extraction_source")
            ),
            "type_confidence": metadata.get(
                "type_confidence", existing.get("type_confidence")
            ),
            "type_detected": metadata.get("type_detected", existing.get("type_detected")),
            "needs_review": metadata.get("needs_review", existing.get("needs_review", False)),
            "user_edited_fields": edited_fields,
        }
    )
    client = _client()
    if extraction_error:
        extracted_json["extraction_error"] = extraction_error
    if client is None:
        with _memory_lock:
            row = _documents.get(document_id)
            if row is None or row["user_id"] != user_id:
                return None
            row["type"] = extracted_json["document_type"]
            row["status"] = status.value
            row["extracted_json"] = extracted_json
            return _record(row)
    response = (
        client.table("documents")
        .update(
            {
                "type": extracted_json["document_type"],
                "status": status.value,
                "extracted_json": extracted_json,
            }
        )
        .eq("id", document_id)
        .eq("user_id", user_id)
        .select("*")
        .execute()
    )
    row = _first(response)
    return _record(row) if row else None


def correct_document(
    user_id: str, document_id: str, corrections: dict[str, Any]
) -> dict[str, Any] | None:
    existing = get_document(user_id, document_id)
    if existing is None:
        return None
    document = FinancialDocument.model_validate(existing)
    updated = document.model_copy(update=corrections)
    client = _client()
    extracted_json = _document_fields(updated)
    extracted_json.update(
        {
            "envelope": existing.get("extraction_envelope"),
            "extraction_source": existing.get("extraction_source"),
            "type_confidence": existing.get("type_confidence"),
            "type_detected": existing.get("type_detected"),
            "needs_review": existing.get("needs_review", False),
            "user_edited_fields": sorted(
                set(existing.get("user_edited_fields", [])) | set(corrections)
            ),
        }
    )
    if client is None:
        with _memory_lock:
            row = _documents.get(document_id)
            if row is None or row["user_id"] != user_id:
                return None
            row["type"] = updated.document_type.value
            row["extracted_json"] = extracted_json
            row["status"] = DocumentStatus.EXTRACTED.value
            return _record(row)
    response = (
        client.table("documents")
        .update(
            {
                "type": updated.document_type.value,
                "status": DocumentStatus.EXTRACTED.value,
                "extracted_json": extracted_json,
            }
        )
        .eq("id", document_id)
        .eq("user_id", user_id)
        .select("*")
        .execute()
    )
    row = _first(response)
    return _record(row) if row else None


def download_document(user_id: str, document_id: str) -> bytes | None:
    record = get_document(user_id, document_id)
    if record is None:
        return None
    if _client() is None:
        return _document_files.get(document_id)
    settings = get_settings()
    return _client().storage.from_(settings.supabase_storage_bucket).download(record["storage_path"])


def delete_document(user_id: str, document_id: str) -> bool:
    record = get_document(user_id, document_id)
    if record is None:
        return False
    client = _client()
    if client is None:
        _documents.pop(document_id, None)
        _document_files.pop(document_id, None)
        for run_id, report in list(_runs.items()):
            if any(document.id == document_id for document in report.documents):
                _runs.pop(run_id)
        return True
    settings = get_settings()
    client.storage.from_(settings.supabase_storage_bucket).remove([record["storage_path"]])
    related_runs = (
        client.table("validation_runs")
        .select("id")
        .eq("user_id", user_id)
        .contains("document_ids", [document_id])
        .execute()
        .data
    )
    if related_runs:
        client.table("validation_runs").delete().eq("user_id", user_id).in_(
            "id", [run["id"] for run in related_runs]
        ).execute()
    client.table("documents").delete().eq("id", document_id).eq("user_id", user_id).execute()
    return True


def create_validation_run(
    user_id: str, documents: list[FinancialDocument], findings: list[Finding]
) -> ValidationReport:
    run_id = str(uuid4())
    created_at = datetime.now(UTC)
    summaries = [
        {
            "id": doc.id,
            "filename": doc.filename,
            "document_type": doc.document_type.value,
            "amount": doc.amount,
            "currency": doc.currency,
            "term": doc.term,
            "deadline": doc.deadline,
            "required_credits": doc.required_credits,
        }
        for doc in documents
    ]
    summary = (
        f"{len(findings)} potential {'inconsistency' if len(findings) == 1 else 'inconsistencies'} found."
        if findings
        else "No potential inconsistencies detected."
    )
    report = ValidationReport(
        id=run_id,
        created_at=created_at,
        documents=summaries,
        findings=findings,
        summary=summary,
    )
    client = _client()
    if client is None:
        _runs[run_id] = report
        return report
    client.table("validation_runs").insert(
        {
            "id": run_id,
            "user_id": user_id,
            "created_at": created_at.isoformat(),
            "document_ids": [doc.id for doc in documents],
        }
    ).execute()
    if findings:
        try:
            client.table("findings").insert(
                [
                    {
                        "run_id": run_id,
                        "rule_id": finding.rule_id,
                        "severity": finding.severity.value,
                        "title": finding.title,
                        "explanation": finding.explanation,
                        "document_ids": finding.document_ids,
                        "fields": {
                            key: str(value) if isinstance(value, Decimal) else value
                            for key, value in finding.fields.items()
                        },
                        "suggested_action": finding.suggested_action,
                        "details": finding.model_dump(
                            mode="json",
                            exclude={
                                "rule_id",
                                "severity",
                                "title",
                                "explanation",
                                "document_ids",
                                "fields",
                                "suggested_action",
                            },
                        ),
                    }
                    for finding in findings
                ]
            ).execute()
        except Exception:
            client.table("validation_runs").delete().eq("id", run_id).eq("user_id", user_id).execute()
            raise
    return report


def get_validation_run(user_id: str, run_id: str) -> ValidationReport | None:
    client = _client()
    if client is None:
        report = _runs.get(run_id)
        return report if report and all(_documents.get(doc.id, {}).get("user_id") == user_id for doc in report.documents) else None

    run = _first(
        client.table("validation_runs")
        .select("*")
        .eq("id", run_id)
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )
    if run is None:
        return None
    document_rows = (
        client.table("documents")
        .select("*")
        .eq("user_id", user_id)
        .in_("id", run["document_ids"])
        .execute()
        .data
    )
    documents_by_id = {row["id"]: _record(row) for row in document_rows}
    finding_rows = (
        client.table("findings")
        .select("*")
        .eq("run_id", run_id)
        .order("created_at")
        .execute()
        .data
    )
    return ValidationReport(
        id=run["id"],
        created_at=run["created_at"],
        documents=[
            {
                key: row[key]
                for key in (
                    "id",
                    "filename",
                    "document_type",
                    "amount",
                    "currency",
                    "term",
                    "deadline",
                    "required_credits",
                )
            }
            for document_id in run["document_ids"]
            if (row := documents_by_id.get(document_id)) is not None
        ],
        findings=[_finding_from_row(row) for row in finding_rows],
        summary=(
            f"{len(finding_rows)} potential {'inconsistency' if len(finding_rows) == 1 else 'inconsistencies'} found."
            if finding_rows
            else "No potential inconsistencies detected."
        ),
    )


def clear_repositories() -> None:
    """Clear local demo state for isolated tests."""
    _documents.clear()
    _document_files.clear()
    _runs.clear()
