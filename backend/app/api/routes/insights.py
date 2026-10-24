from fastapi import APIRouter, HTTPException

from app.db.repositories import get_report
from app.schemas.insights import InsightsResponse
from app.services.insights.advisor import summarize_report

router = APIRouter(prefix="/insights", tags=["insights"])


@router.get("/{report_id}", response_model=InsightsResponse)
def get_insights(report_id: str) -> InsightsResponse:
    report = get_report(report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Validation report not found.")
    return summarize_report(report)
