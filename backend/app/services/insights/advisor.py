from decimal import Decimal

from app.schemas.insights import InsightsResponse
from app.schemas.validation import ValidationReport


def summarize_report(
    report: ValidationReport, ledger: dict | None = None
) -> InsightsResponse:
    errors = [finding for finding in report.findings if finding.severity.value == "error"]
    warnings = [
        finding for finding in report.findings if finding.severity.value == "warning"
    ]
    recommendations: list[str] = []
    if errors:
        recommendations.append(
            "Start with the error-severity findings, especially overdue deadlines or confirmed amount differences."
        )
    if warnings:
        recommendations.append(
            "Confirm the flagged balances, award postings, or schedule differences with the named office before paying."
        )
    if report.findings:
        categories = sorted(
            {finding.category for finding in report.findings if finding.category}
        )
        if categories:
            recommendations.append(
                "Review the findings by category: " + ", ".join(categories) + "."
            )
    deadlines = [doc.deadline for doc in report.documents if doc.deadline is not None]
    if deadlines:
        recommendations.append(f"Add the earliest listed date ({min(deadlines).isoformat()}) to your calendar and verify what action is due.")
    if ledger:
        term_balances = [
            (term, currency, values.get("gap"))
            for term, currencies in ledger.get("terms", {}).items()
            for currency, values in currencies.items()
            if Decimal(str(values.get("gap", "0"))) > 0
        ]
        if term_balances:
            term, currency, gap = max(
                term_balances, key=lambda item: Decimal(str(item[2]))
            )
            recommendations.append(
                f"The current ledger shows the largest listed gap in {term}: {currency} {Decimal(str(gap)):,.2f}."
            )
    if not recommendations:
        recommendations.append("No cross-document conflicts were detected in the fields the app could read. Verify any missing details with the issuer.")
    if report.findings:
        noun = "finding" if len(report.findings) == 1 else "findings"
        headline = f"Review {len(report.findings)} potential {noun}."
    else:
        headline = "No potential inconsistencies found in the extracted fields."
    return InsightsResponse(report_id=report.id, headline=headline, recommendations=recommendations)
