from fastapi import APIRouter, HTTPException

from app.api.deps import CurrentUser, current_user_id
from app.db.repositories import get_validation_run
from app.schemas.insights import InsightsResponse
from app.schemas.validation import InsightsRequest
from app.services.insights.advisor import summarize_report

router = APIRouter(prefix="/insights", tags=["insights"])


@router.post("", response_model=InsightsResponse)
def create_insights(request: InsightsRequest, user: CurrentUser) -> InsightsResponse:
    report = get_validation_run(current_user_id(user), str(request.run_id))
    if report is None:
        raise HTTPException(status_code=404, detail="Validation report not found.")
    return summarize_report(report)
