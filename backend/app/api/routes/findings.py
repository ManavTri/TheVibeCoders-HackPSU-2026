from fastapi import APIRouter

from app.api.deps import CurrentUser, current_user_id
from app.db.repositories import get_current_findings
from app.schemas.validation import Finding

router = APIRouter(prefix="/findings", tags=["findings"])


@router.get("", response_model=list[Finding])
def current_findings(user: CurrentUser) -> list[Finding]:
    return get_current_findings(current_user_id(user))
