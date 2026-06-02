import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _uuid() -> str:
    return str(uuid.uuid4())


class Submission(Base):
    __tablename__ = "submissions"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    assignment_id: Mapped[str] = mapped_column(String, nullable=False)
    student_id: Mapped[str] = mapped_column(String, nullable=False)
    # text | file
    submit_type: Mapped[str] = mapped_column(String, nullable=False)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    file_path: Mapped[str | None] = mapped_column(String, nullable=True)
    # C++ pybind11 提取的文本
    extracted_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    # submitted
    status: Mapped[str] = mapped_column(String, default="submitted")
