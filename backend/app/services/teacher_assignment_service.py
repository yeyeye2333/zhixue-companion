"""教师端作业发布与管理服务"""
import os

from fastapi import HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.assignment import Assignment
from app.models.submission import Submission
from app.models.user import User
from app.schemas.teacher_assignment import AssignmentUpdateRequest
from app.services import file_processor_client


def publish_assignment(
    teacher_id: str,
    title: str,
    course: str,
    description: str,
    due_at,
    reference_answer: str | None,
    rubric: str | None,
    attachment: UploadFile | None,
    db: Session,
) -> Assignment:
    attachment_path = None
    attachment_text = None

    if attachment:
        ext = (attachment.filename or "").rsplit(".", 1)[-1].lower()
        if ext not in settings.allowed_extensions:
            raise HTTPException(status_code=400, detail=f"不支持的附件格式：{ext}")
        filename = f"assignment_{teacher_id}_{attachment.filename}"
        save_path = os.path.join(settings.upload_dir, filename)
        with open(save_path, "wb") as f:
            f.write(attachment.file.read())
        attachment_path = save_path
        # C++ pybind11 解析题目文本
        attachment_text = file_processor_client.extract_text(save_path)

    a = Assignment(
        teacher_id=teacher_id,
        title=title,
        course=course,
        description=description,
        reference_answer=reference_answer,
        rubric=rubric,
        attachment_path=attachment_path,
        attachment_text=attachment_text,
        due_at=due_at,
    )
    db.add(a)
    db.commit()
    db.refresh(a)
    return a


def list_assignments(teacher_id: str, course: str | None, status: str | None, db: Session) -> dict:
    q = db.query(Assignment).filter(Assignment.teacher_id == teacher_id)
    if course:
        q = q.filter(Assignment.course == course)
    if status:
        q = q.filter(Assignment.status == status)
    assignments = q.order_by(Assignment.created_at.desc()).all()

    items = []
    for a in assignments:
        sub_count = db.query(Submission).filter(Submission.assignment_id == a.id).count()
        items.append({
            "id": a.id, "title": a.title, "course": a.course,
            "due_at": a.due_at, "status": a.status,
            "submission_count": sub_count, "total_students": 0,  # 可扩展班级人数
        })
    return {"items": items, "total": len(items)}


def get_assignment(assignment_id: str, teacher_id: str, db: Session) -> dict:
    a = _get_own_assignment(assignment_id, teacher_id, db)
    sub_count = db.query(Submission).filter(Submission.assignment_id == a.id).count()
    attachment_url = f"/files/{os.path.basename(a.attachment_path)}" if a.attachment_path else None
    return {
        "id": a.id, "title": a.title, "course": a.course,
        "description": a.description, "reference_answer": a.reference_answer,
        "rubric": a.rubric, "due_at": a.due_at, "status": a.status,
        "attachment_url": attachment_url, "submission_count": sub_count,
        "created_at": a.created_at, "updated_at": a.updated_at,
    }


def update_assignment(assignment_id: str, teacher_id: str, req: AssignmentUpdateRequest, db: Session) -> Assignment:
    a = _get_own_assignment(assignment_id, teacher_id, db)
    for field, value in req.model_dump(exclude_none=True).items():
        setattr(a, field, value)
    db.commit()
    db.refresh(a)
    return a


def close_assignment(assignment_id: str, teacher_id: str, db: Session) -> Assignment:
    a = _get_own_assignment(assignment_id, teacher_id, db)
    a.status = "closed"
    db.commit()
    db.refresh(a)
    return a


def list_submissions(assignment_id: str, teacher_id: str, db: Session) -> dict:
    _get_own_assignment(assignment_id, teacher_id, db)
    subs = db.query(Submission).filter(Submission.assignment_id == assignment_id).all()
    items = []
    for s in subs:
        student = db.get(User, s.student_id)
        items.append({
            "id": s.id, "student_id": s.student_id,
            "student_name": student.name if student else "未知",
            "submit_type": s.submit_type,
            "submitted_at": s.submitted_at, "status": s.status,
        })
    return {"assignment_id": assignment_id, "items": items, "total": len(items)}


def _get_own_assignment(assignment_id: str, teacher_id: str, db: Session) -> Assignment:
    a = db.get(Assignment, assignment_id)
    if not a:
        raise HTTPException(status_code=404, detail="作业不存在")
    if a.teacher_id != teacher_id:
        raise HTTPException(status_code=403, detail="无权操作此作业")
    return a
