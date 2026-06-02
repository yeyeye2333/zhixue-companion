from datetime import datetime

from pydantic import BaseModel


# ── 学生端请求 ────────────────────────────────────────────────

class TextSubmitRequest(BaseModel):
    content: str
    submit_type: str = "text"


# ── 响应体 ────────────────────────────────────────────────────

class AssignmentBriefOut(BaseModel):
    id: str
    title: str
    course: str
    due_at: datetime
    status: str
    submitted: bool


class AssignmentDetailOut(BaseModel):
    id: str
    title: str
    course: str
    description: str
    due_at: datetime
    status: str
    attachment_url: str | None = None
    submitted: bool


class SubmissionOut(BaseModel):
    id: str
    assignment_id: str
    student_id: str
    submit_type: str
    submitted_at: datetime
    status: str


class MySubmissionOut(BaseModel):
    id: str
    assignment_id: str
    submit_type: str
    file_url: str | None = None
    submitted_at: datetime
    status: str
