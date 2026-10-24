from app.schemas.insights import InsightsResponse
from app.schemas.validation import ValidationReport


def summarize_report(report: ValidationReport) -> InsightsResponse:
    error_count = sum(finding.severity.value == "error" for finding in report.findings)
    warning_count = sum(finding.severity.value == "warning" for finding in report.findings)
    recommendations: list[str] = []
    if report.findings:
        recommendations.append("Confirm flagged details with the issuer or your financial-aid office before making a payment decision.")
    if error_count:
        recommendations.append("Resolve the academic-term discrepancy first; award eligibility may depend on the term.")
    if warning_count:
        recommendations.append("Review award amounts and enrollment requirements with the relevant office.")
    deadlines = [doc.deadline for doc in report.documents if doc.deadline is not None]
    if deadlines:
        recommendations.append(f"Add the earliest listed date ({min(deadlines).isoformat()}) to your calendar and verify what action is due.")
    if not recommendations:
        recommendations.append("No cross-document conflicts were detected in the fields the app could read. Verify any missing details with the issuer.")
    if report.findings:
        noun = "finding" if len(report.findings) == 1 else "findings"
        headline = f"Review {len(report.findings)} potential {noun}."
    else:
        headline = "No potential inconsistencies found in the extracted fields."
    return InsightsResponse(report_id=report.id, headline=headline, recommendations=recommendations)
