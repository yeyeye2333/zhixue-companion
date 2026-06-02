from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.auth import LoginRequest, LoginResponse, MeResponse, RegisterResponse, StudentRegisterRequest, TeacherRegisterRequest
from app.services import auth_service
from app.services.auth_service import get_current_user

router = APIRouter(tags=["认证"])


def _ok(data, message="ok", status_code=200):
    return {"success": True, "data": data, "message": message}


@router.post("/auth/register/student", status_code=201)
def register_student(req: StudentRegisterRequest, db: Session = Depends(get_db)):
    user = auth_service.register_student(req, db)
    return _ok(RegisterResponse(id=user.id, username=user.username, name=user.name, role=user.role), "registered")


@router.post("/auth/register/teacher", status_code=201)
def register_teacher(req: TeacherRegisterRequest, db: Session = Depends(get_db)):
    user = auth_service.register_teacher(req, db)
    return _ok(RegisterResponse(id=user.id, username=user.username, name=user.name, role=user.role), "registered")


@router.post("/auth/login")
def login(req: LoginRequest, db: Session = Depends(get_db)):
    result = auth_service.login(req, db)
    return _ok(result)


@router.get("/auth/me")
def me(current_user=Depends(get_current_user)):
    return _ok(MeResponse(
        id=current_user.id,
        username=current_user.username,
        name=current_user.name,
        role=current_user.role,
        extra=current_user.extra or {},
    ))
