"""
测试公共 fixture。

使用内存 SQLite，每个测试函数独享一个干净的数据库实例，
不依赖任何外部服务（MiniMax / ChromaDB / pgvector）。
"""
import uuid

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.db.session import Base

# ── 数据库 fixture ────────────────────────────────────────────


@pytest.fixture(scope="function")
def db():
    """
    每个测试函数获得一个全新的内存 SQLite 数据库。
    scope="function" 保证测试之间完全隔离，不会相互污染。
    """
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    # 导入所有模型，触发 mapper 注册后再建表
    import app.models.announcement    # noqa: F401
    import app.models.assignment      # noqa: F401
    import app.models.chat            # noqa: F401
    import app.models.course          # noqa: F401
    import app.models.discussion      # noqa: F401
    import app.models.grade           # noqa: F401
    import app.models.learning_plan   # noqa: F401
    import app.models.plan_progress   # noqa: F401
    import app.models.question        # noqa: F401
    import app.models.quiz            # noqa: F401
    import app.models.section         # noqa: F401
    import app.models.submission      # noqa: F401
    import app.models.summary         # noqa: F401
    import app.models.user            # noqa: F401

    Base.metadata.create_all(bind=engine)
    _Session = sessionmaker(bind=engine)
    session = _Session()
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


# ── 基础数据 fixture ──────────────────────────────────────────


@pytest.fixture
def make_user(db: Session):
    """工厂：创建用户，返回 User 对象。"""
    from app.models.user import User

    def _make(role: str = "student", extra: dict | None = None) -> User:
        from app.core.security import hash_password
        user = User(
            id=str(uuid.uuid4()),
            username=f"user_{uuid.uuid4().hex[:6]}",
            name="测试用户",
            role=role,
            password_hash=hash_password("password123"),
            extra=extra or {},
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    return _make


@pytest.fixture
def make_course(db: Session):
    """工厂：创建课程，返回 Course 对象。"""
    from app.models.course import Course

    def _make(teacher_id: str) -> Course:
        course = Course(
            id=str(uuid.uuid4()),
            name="测试课程",
            code="TEST01",
            teacher_id=teacher_id,
        )
        db.add(course)
        db.commit()
        db.refresh(course)
        return course

    return _make


@pytest.fixture
def enroll(db: Session):
    """工厂：将学生加入课程（创建 CourseEnrollment 记录）。"""
    from app.models.course import CourseEnrollment

    def _enroll(course_id: str, student_id: str) -> None:
        enrollment = CourseEnrollment(course_id=course_id, student_id=student_id)
        db.add(enrollment)
        db.commit()

    return _enroll
