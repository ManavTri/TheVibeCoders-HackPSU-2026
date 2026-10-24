from pydantic import BaseModel


class InsightsResponse(BaseModel):
    report_id: str
    headline: str
    recommendations: list[str]
    disclaimer: str = "Planning support only; confirm amounts, deadlines, and eligibility with your school or award provider."
