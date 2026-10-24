from app.schemas.insights import InsightsResponse
from app.schemas.validation import ValidationReport


def summarize_report(report: ValidationReport) -> InsightsResponse:
    high_count = sum(finding.severity.value == "high" for finding in report.findings)
    medium_count = sum(finding.severity.value == "medium" for finding in report.findings)
    recommendations: list[str] = []
    if report.findings:
        recommendations.append("Contact the issuer or your financial-aid office to confirm each flagged detail before making a payment decision.")
    if high_count:
        recommendations.append("Resolve the academic-term discrepancy first; award eligibility may depend on the term.")
    if medium_count:
        recommendations.append("Compare award and bill amounts and ask how any remaining award balance is disbursed.")
    deadlines = [doc.deadline for doc in report.documents if doc.deadline is not None]
    if deadlines:
        recommendations.append(f"Add the earliest listed date ({min(deadlines).isoformat()}) to your calendar and verify what action is due.")
    if not recommendations:
        recommendations.append("No cross-document conflicts were detected in the fields the app could read. Verify any missing details with the issuer.")
    if report.findings:
        noun = "inconsistency" if len(report.findings) == 1 else "inconsistencies"
        headline = f"Review {len(report.findings)} potential {noun}."
    else:
        headline = "No potential inconsistencies found in the extracted fields."
    return InsightsResponse(report_id=report.id, headline=headline, recommendations=recommendations)
