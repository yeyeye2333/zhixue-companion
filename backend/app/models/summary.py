import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _uuid() -> str:
    return str(uuid.uuid4())


class Summary(Base):
    __tablename__ = "summaries"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String, nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    course: Mapped[str | None] = mapped_column(String, nullable=True)
    source_text: Mapped[str] = mapped_column(Text, nullable=False)
    # structured | brief | review
    summary_type: Mapped[str] = mapped_column(String, default="structured")
    result: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
