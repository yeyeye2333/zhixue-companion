"""个性化学习计划服务"""
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.learning_plan import LearningPlan
from app.schemas.learning_plan import LearningPlanCreateRequest
from app.services import minimax_client


def create_plan(req: LearningPlanCreateRequest, student_id: str, db: Session) -> LearningPlan:
    basis = {
        "goal": req.goal,
        "grade_records": [r.model_dump() for r in req.grade_records],
        "homework_records": [r.model_dump() for r in req.homework_records],
        "available_time_per_day": req.available_time_per_day,
    }
    result = minimax_client.generate_learning_plan(
        req.course, req.goal, basis, req.available_time_per_day
    )
    plan = LearningPlan(
        student_id=student_id,
        course=req.course,
        basis=basis,
        plan=result.get("plan", []),
        analysis=result.get("analysis", {}),
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return plan


def list_plans(student_id: str, course: str | None, status: str | None, db: Session) -> dict:
    q = db.query(LearningPlan).filter(LearningPlan.student_id == student_id)
    if course:
        q = q.filter(LearningPlan.course == course)
    if status:
        q = q.filter(LearningPlan.status == status)
    items = q.order_by(LearningPlan.created_at.desc()).all()
    return {"items": items, "total": len(items)}
