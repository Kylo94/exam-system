"""
FastAPI应用入口
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse

from app.config import settings
from app.database import init_db, close_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时
    print("🚀 应用启动中...")
    await init_db()
    yield
    # 关闭时
    print("👋 应用关闭...")
    await close_db()


# 创建FastAPI应用
app = FastAPI(
    title=settings.APP_NAME,
    version="4.0.0",
    description="在线答题系统 - FastAPI重构版",
    lifespan=lifespan,
)

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册Jinja2模板
from app.templating import templates

# 挂载静态文件
import os
if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")

# 注册路由
from app.routers import auth, main, admin, teacher, student, api
app.include_router(main.router)
app.include_router(auth.router, prefix="/auth", tags=["认证"])
app.include_router(admin.router, prefix="/admin", tags=["管理员"])
app.include_router(teacher.router, prefix="/teacher", tags=["教师"])
app.include_router(student.router, prefix="/student", tags=["学生"])
app.include_router(api.router, prefix="/api", tags=["API"])


# 全局异常处理
@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """通用异常处理"""
    return templates.TemplateResponse(
        "error.html",
        {"request": request, "error": str(exc)},
        status_code=500
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )
