from datetime import datetime

from pydantic import BaseModel


# ── 请求体 ────────────────────────────────────────────────────

class SummaryCreateRequest(BaseModel):
    title: str
    course: str | None = None
    source_text: str
    summary_type: str = "structured"  # structured | brief | review


# ── 响应体 ────────────────────────────────────────────────────

class SummaryOut(BaseModel):
    id: str
    title: str
    course: str | None
    summary: dict
    created_at: datetime


class SummaryDetailOut(BaseModel):
    id: str
    title: str
    course: str | None
    source_text: str
    summary: dict
    created_at: datetime


class SummaryBriefOut(BaseModel):
    id: str
    title: str
    course: str | None
    created_at: datetime
