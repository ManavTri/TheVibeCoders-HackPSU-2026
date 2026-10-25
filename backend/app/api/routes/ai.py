from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import CurrentUser, current_user_id
from app.core.config import get_settings
from app.schemas.ai import ActionResult, ChatRequest, ChatResponse
from app.services.ai.agent import (
    ActionExpiredError,
    ActionNotFoundError,
    ChatBusyError,
    ChatRateLimitError,
    ChatUnavailableError,
    cancel_action,
    chat,
    confirm_action,
)
from app.services.extraction.client import create_gemini_client

router = APIRouter(prefix="/ai", tags=["ai"])


def get_ai_client() -> Any:
    settings = get_settings()
    if not settings.llm_enabled or not settings.llm_model:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The financial assistant is temporarily unavailable. Please try again.",
        )
    try:
        return create_gemini_client(
            settings.llm_api_key or "", min(settings.llm_timeout_seconds, 40)
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The financial assistant is temporarily unavailable. Please try again.",
        ) from exc


@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(
    request: ChatRequest,
    user: CurrentUser,
    client: Annotated[Any, Depends(get_ai_client)],
) -> ChatResponse:
    try:
        return await chat(current_user_id(user), request, client=client)
    except ChatRateLimitError as exc:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Chat request limit reached. Please wait before trying again.",
            headers={"Retry-After": str(exc.retry_after)},
        ) from exc
    except ChatBusyError as exc:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="A chat request is already in progress.",
            headers={"Retry-After": "1"},
        ) from exc
    except ChatUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The financial assistant is temporarily unavailable. Please try again.",
        ) from exc


@router.post("/actions/{action_id}/confirm", response_model=ActionResult)
def confirm_chat_action(action_id: UUID, user: CurrentUser) -> ActionResult:
    try:
        result = confirm_action(current_user_id(user), str(action_id))
    except ActionNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Pending action not found.") from exc
    except ActionExpiredError as exc:
        raise HTTPException(status_code=410, detail="Pending action has expired.") from exc
    except Exception as exc:
        raise HTTPException(
            status_code=409,
            detail="The pending action could not be completed. Review the document and try again.",
        ) from exc
    return ActionResult(
        status="confirmed",
        message=f"Action completed for {result['filename']}.",
    )


@router.post("/actions/{action_id}/cancel", response_model=ActionResult)
def cancel_chat_action(action_id: UUID, user: CurrentUser) -> ActionResult:
    try:
        cancel_action(current_user_id(user), str(action_id))
    except ActionNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Pending action not found.") from exc
    return ActionResult(status="cancelled", message="Pending action cancelled.")
