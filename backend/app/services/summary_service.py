"""知识点总结服务"""
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.summary import Summary
from app.schemas.summary import SummaryCreateRequest
from app.services import minimax_client


def create_summary(req: SummaryCreateRequest, user_id: str, db: Session) -> Summary:
    result = minimax_client.generate_summary(
        req.title, req.source_text, req.summary_type, req.course
    )
    s = Summary(
        user_id=user_id,
        title=req.title,
        course=req.course,
        source_text=req.source_text,
        summary_type=req.summary_type,
        result=result,
    )
    db.add(s)
    db.commit()
    db.refresh(s)
    return s


def list_summaries(user_id: str, course: str | None, keyword: str | None, db: Session) -> dict:
    q = db.query(Summary).filter(Summary.user_id == user_id)
    if course:
        q = q.filter(Summary.course == course)
    if keyword:
        q = q.filter(Summary.title.contains(keyword))
    items = q.order_by(Summary.created_at.desc()).all()
    return {"items": items, "total": len(items)}


def get_summary(summary_id: str, user_id: str, db: Session) -> Summary:
    s = db.get(Summary, summary_id)
    if not s or s.user_id != user_id:
        raise HTTPException(status_code=404, detail="总结不存在")
    return s


def delete_summary(summary_id: str, user_id: str, db: Session) -> None:
    s = db.get(Summary, summary_id)
    if not s or s.user_id != user_id:
        raise HTTPException(status_code=404, detail="总结不存在")
    db.delete(s)
    db.commit()
