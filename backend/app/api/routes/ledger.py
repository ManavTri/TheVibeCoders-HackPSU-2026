from datetime import date
from typing import Any

from fastapi import APIRouter

from app.api.deps import CurrentUser, current_user_id
from app.db.repositories import get_current_ledger

router = APIRouter(prefix="/ledger", tags=["ledger"])


@router.get("")
def current_ledger(user: CurrentUser) -> dict[str, Any]:
    return get_current_ledger(current_user_id(user), today=date.today())
