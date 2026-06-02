import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.db.init_db import init_db

# 模块加载时立即创建必要目录，确保 StaticFiles mount 不报错
os.makedirs(settings.upload_dir, exist_ok=True)
os.makedirs(settings.log_dir, exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时建表（目录已在上方创建）
    init_db()
    yield


app = FastAPI(title="智学伴侣 API", version="0.1.0", lifespan=lifespan)

# CORS（开发阶段允许所有来源，生产环境按需收窄）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 上传文件静态访问
app.mount("/files", StaticFiles(directory=settings.upload_dir), name="files")

# ── 注册路由 ──────────────────────────────────────────────────
from app.api import (  # noqa: E402
    routes_auth,
    routes_chat,
    routes_student_assignments,
    routes_summary,
    routes_learning_plans,
    routes_teacher_assignments,
)

app.include_router(routes_auth.router, prefix="/api")
app.include_router(routes_chat.router, prefix="/api")
app.include_router(routes_student_assignments.router, prefix="/api")
app.include_router(routes_summary.router, prefix="/api")
app.include_router(routes_learning_plans.router, prefix="/api")
app.include_router(routes_teacher_assignments.router, prefix="/api")


# ── 健康检查 ──────────────────────────────────────────────────
@app.get("/api/health")
def health():
    return {"success": True, "data": {"status": "ok", "service": "zhixue-companion-api"}, "message": "ok"}


# ── 全局异常处理 ──────────────────────────────────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={"success": False, "error": {"code": "INTERNAL_ERROR", "message": str(exc)}},
    )
