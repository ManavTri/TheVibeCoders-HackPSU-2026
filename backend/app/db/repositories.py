"""In-memory demo repository; replace with Supabase repositories for shared persistence."""

from app.schemas.validation import ValidationReport

_reports: dict[str, ValidationReport] = {}


def save_report(report: ValidationReport) -> None:
    _reports[report.id] = report


def get_report(report_id: str) -> ValidationReport | None:
    return _reports.get(report_id)


def list_reports() -> list[ValidationReport]:
    return list(reversed(list(_reports.values())))


def clear_reports() -> None:
    _reports.clear()
