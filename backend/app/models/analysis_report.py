import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _uuid() -> str:
    return str(uuid.uuid4())


class AnalysisReport(Base):
    __tablename__ = "analysis_reports"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    assignment_id: Mapped[str] = mapped_column(String, nullable=False)
    suspicious_pairs: Mapped[list] = mapped_column(JSON, default=list)
    comparison_details: Mapped[list] = mapped_column(JSON, default=list)
    common_issues: Mapped[list] = mapped_column(JSON, default=list)
    teaching_suggestions: Mapped[list] = mapped_column(JSON, default=list)
    fingerprint_data: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
