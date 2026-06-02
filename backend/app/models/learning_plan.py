import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _uuid() -> str:
    return str(uuid.uuid4())


class LearningPlan(Base):
    __tablename__ = "learning_plans"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    student_id: Mapped[str] = mapped_column(String, nullable=False)
    course: Mapped[str] = mapped_column(String, nullable=False)
    basis: Mapped[dict] = mapped_column(JSON, default=dict)
    plan: Mapped[list] = mapped_column(JSON, default=list)
    analysis: Mapped[dict] = mapped_column(JSON, default=dict)
    # active | completed | archived
    status: Mapped[str] = mapped_column(String, default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
