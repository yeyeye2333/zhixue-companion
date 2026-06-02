from datetime import datetime

from pydantic import BaseModel


# ── 请求体 ────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    question: str
    course: str | None = None
    session_id: str | None = None


# ── 响应体 ────────────────────────────────────────────────────

class ChatResponse(BaseModel):
    session_id: str
    answer: str
    suggestions: list[str] = []


class MessageOut(BaseModel):
    id: str
    role: str
    content: str
    created_at: datetime


class SessionMessagesResponse(BaseModel):
    session_id: str
    messages: list[MessageOut]
