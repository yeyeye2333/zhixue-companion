from pydantic import BaseModel, Field


# ── 请求体 ────────────────────────────────────────────────────

class StudentRegisterRequest(BaseModel):
    username: str = Field(..., description="学号")
    name: str
    class_name: str
    password: str = Field(..., min_length=6, max_length=32)


class TeacherRegisterRequest(BaseModel):
    username: str = Field(..., description="工号")
    name: str
    courses: list[str]
    password: str = Field(..., min_length=6, max_length=32)


class LoginRequest(BaseModel):
    username: str
    password: str


# ── 响应体 ────────────────────────────────────────────────────

class UserOut(BaseModel):
    id: str
    username: str
    name: str
    role: str


class RegisterResponse(BaseModel):
    id: str
    username: str
    name: str
    role: str


class LoginResponse(BaseModel):
    token: str
    expires_in: int
    user: UserOut


class MeResponse(BaseModel):
    id: str
    username: str
    name: str
    role: str
    extra: dict
