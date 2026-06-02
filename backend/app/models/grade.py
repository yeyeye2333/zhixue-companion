import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _uuid() -> str:
    return str(uuid.uuid4())


class AIGradingResult(Base):
    __tablename__ = "ai_grading_results"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    submission_id: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    ai_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    comments: Mapped[str | None] = mapped_column(Text, nullable=True)
    deductions: Mapped[list] = mapped_column(JSON, default=list)
    suggestions: Mapped[list] = mapped_column(JSON, default=list)
    confirmed: Mapped[bool] = mapped_column(Boolean, default=False)
    final_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    teacher_comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
