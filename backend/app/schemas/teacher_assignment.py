from datetime import datetime

from pydantic import BaseModel


# ── 教师端请求 ────────────────────────────────────────────────

class AssignmentUpdateRequest(BaseModel):
    title: str | None = None
    description: str | None = None
    reference_answer: str | None = None
    rubric: str | None = None
    due_at: datetime | None = None


class GradeRequest(BaseModel):
    submission_ids: list[str]
    need_teacher_confirm: bool = True


class GradeConfirmRequest(BaseModel):
    final_score: float
    confirmed: bool = True
    teacher_comment: str | None = None


class AnalyzeRequest(BaseModel):
    submission_ids: list[str]
    similarity_threshold: float = 0.8
    compare_dimensions: list[str] = ["structure", "concept", "expression", "conclusion"]


# ── 响应体 ────────────────────────────────────────────────────

class AssignmentPublishedOut(BaseModel):
    id: str
    title: str
    course: str
    description: str
    due_at: datetime
    status: str
    attachment_url: str | None = None
    created_at: datetime


class AssignmentListItemOut(BaseModel):
    id: str
    title: str
    course: str
    due_at: datetime
    status: str
    submission_count: int
    total_students: int


class AssignmentFullOut(BaseModel):
    id: str
    title: str
    course: str
    description: str
    reference_answer: str | None = None
    rubric: str | None = None
    due_at: datetime
    status: str
    attachment_url: str | None = None
    submission_count: int
    created_at: datetime
    updated_at: datetime


class SubmissionListItemOut(BaseModel):
    id: str
    student_id: str
    student_name: str
    submit_type: str
    submitted_at: datetime
    status: str


class GradingResultOut(BaseModel):
    submission_id: str
    student_id: str
    student_name: str
    ai_score: float | None
    comments: str | None
    deductions: list
    suggestions: list
    confirmed: bool


class GradingReportOut(BaseModel):
    assignment_id: str
    average_score: float | None
    graded_count: int
    common_mistakes: list[str]
    weak_points: list[str]
    teaching_suggestions: list[str]


class SuspiciousPairOut(BaseModel):
    submission_a: str
    student_a: str
    submission_b: str
    student_b: str
    similarity: float
    risk_level: str
    similar_segments: list[str]
    ai_reason: str


class ComparisonDetailOut(BaseModel):
    submission_id: str
    student_name: str
    strengths: list[str]
    weaknesses: list[str]
    dimension_scores: dict


class AnalysisReportOut(BaseModel):
    report_id: str
    assignment_id: str
    suspicious_pairs: list[SuspiciousPairOut]
    comparison_details: list[ComparisonDetailOut]
    common_issues: list[str]
    teaching_suggestions: list[str]
    created_at: datetime
