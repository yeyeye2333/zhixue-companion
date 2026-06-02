from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.summary import SummaryCreateRequest
from app.services import summary_service
from app.services.auth_service import require_student

router = APIRouter(tags=["知识点总结"])


def _ok(data, message="ok"):
    return {"success": True, "data": data, "message": message}


@router.post("/summaries", status_code=201)
def create_summary(req: SummaryCreateRequest, current_user=Depends(require_student), db: Session = Depends(get_db)):
    s = summary_service.create_summary(req, current_user.id, db)
    return _ok({
        "id": s.id, "title": s.title, "course": s.course,
        "summary": s.result, "created_at": s.created_at,
    }, "created")


@router.get("/summaries")
def list_summaries(
    course: str | None = None,
    keyword: str | None = None,
    current_user=Depends(require_student),
    db: Session = Depends(get_db),
):
    result = summary_service.list_summaries(current_user.id, course, keyword, db)
    items = [{"id": s.id, "title": s.title, "course": s.course, "created_at": s.created_at}
             for s in result["items"]]
    return _ok({"items": items, "total": result["total"]})


@router.get("/summaries/{summary_id}")
def get_summary(summary_id: str, current_user=Depends(require_student), db: Session = Depends(get_db)):
    s = summary_service.get_summary(summary_id, current_user.id, db)
    return _ok({
        "id": s.id, "title": s.title, "course": s.course,
        "source_text": s.source_text, "summary": s.result, "created_at": s.created_at,
    })


@router.delete("/summaries/{summary_id}")
def delete_summary(summary_id: str, current_user=Depends(require_student), db: Session = Depends(get_db)):
    summary_service.delete_summary(summary_id, current_user.id, db)
    return _ok({"id": summary_id}, "deleted")
