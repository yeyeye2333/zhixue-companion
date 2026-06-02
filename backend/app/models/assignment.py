import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _uuid() -> str:
    return str(uuid.uuid4())


class Assignment(Base):
    __tablename__ = "assignments"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    teacher_id: Mapped[str] = mapped_column(String, nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    course: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    reference_answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    rubric: Mapped[str | None] = mapped_column(Text, nullable=True)
    attachment_path: Mapped[str | None] = mapped_column(String, nullable=True)
    attachment_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    # open | closed
    status: Mapped[str] = mapped_column(String, default="open")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)
