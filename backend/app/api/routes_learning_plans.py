from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.learning_plan import LearningPlanCreateRequest
from app.services import learning_plan_service
from app.services.auth_service import require_student

router = APIRouter(tags=["个性化学习计划"])


def _ok(data, message="ok"):
    return {"success": True, "data": data, "message": message}


@router.post("/student/learning-plans", status_code=201)
def create_plan(req: LearningPlanCreateRequest, current_user=Depends(require_student), db: Session = Depends(get_db)):
    plan = learning_plan_service.create_plan(req, current_user.id, db)
    return _ok({
        "id": plan.id, "course": plan.course,
        "analysis": plan.analysis, "plan": plan.plan,
        "created_at": plan.created_at,
    }, "created")


@router.get("/student/learning-plans")
def list_plans(
    course: str | None = None,
    status: str | None = None,
    current_user=Depends(require_student),
    db: Session = Depends(get_db),
):
    result = learning_plan_service.list_plans(current_user.id, course, status, db)
    items = [{"id": p.id, "course": p.course, "status": p.status, "created_at": p.created_at}
             for p in result["items"]]
    return _ok({"items": items, "total": result["total"]})
