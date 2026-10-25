from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field, StringConstraints

ChatText = Annotated[str, StringConstraints(min_length=1, max_length=2000)]


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: ChatText


class ChatRequest(BaseModel):
    message: ChatText
    history: list[ChatMessage] = Field(default_factory=list, max_length=12)
    context_documents: list[str] = Field(
        default_factory=list, alias="contextDocuments", max_length=20
    )


class ChatSource(BaseModel):
    document_id: str = Field(alias="documentId")
    filename: str


class PendingAction(BaseModel):
    id: str
    tool: str
    summary: str
    args: dict[str, Any]


class ChatResponse(BaseModel):
    reply: str
    suggestions: list[str] = Field(default_factory=list)
    sources: list[ChatSource] = Field(default_factory=list)
    pending_actions: list[PendingAction] = Field(
        default_factory=list, alias="pendingActions"
    )


class ActionResult(BaseModel):
    status: Literal["confirmed", "cancelled"]
    message: str
    report_id: str | None = Field(default=None, alias="reportId")
