from datetime import datetime

from pydantic import BaseModel


# ── 请求体 ────────────────────────────────────────────────────

class GradeRecord(BaseModel):
    exam_name: str
    score: float
    full_score: float


class HomeworkRecord(BaseModel):
    title: str
    score: float
    full_score: float
    weak_points: list[str] = []


class LearningPlanCreateRequest(BaseModel):
    course: str
    goal: str
    grade_records: list[GradeRecord] = []
    homework_records: list[HomeworkRecord] = []
    available_time_per_day: int = 60  # 分钟


# ── 响应体 ────────────────────────────────────────────────────

class PlanDayItem(BaseModel):
    day: int
    task: str
    duration_minutes: int


class LearningPlanOut(BaseModel):
    id: str
    course: str
    analysis: dict
    plan: list[PlanDayItem]
    created_at: datetime


class LearningPlanBriefOut(BaseModel):
    id: str
    course: str
    status: str
    created_at: datetime
