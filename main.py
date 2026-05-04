"""
FastAPI应用入口
"""
from contextlib import asynccontextmanager
from datetime import datetime
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse

from app.config import settings
from app.database import init_db, close_db
from app.logging_config import setup_logging, get_logger

# 初始化日志系统
setup_logging(
    log_level=settings.LOG_LEVEL,
    log_dir=settings.LOG_DIR,
    max_bytes=settings.LOG_MAX_BYTES,
    backup_count=settings.LOG_BACKUP_COUNT
)
logger = get_logger("app")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时
    logger.info("🚀 应用启动中...")
    await init_db()

    # 初始化应用名称缓存
    from app.templating import init_app_name_cache, load_app_name_async
    init_app_name_cache()
    try:
        await load_app_name_async()
        logger.info("✅ 应用名称缓存加载成功")
    except Exception as e:
        logger.warning(f"⚠️  无法从数据库加载应用名称: {e}")

    yield
    # 关闭时
    logger.info("👋 应用关闭...")
    await close_db()
    logger.info("✅ 数据库连接已关闭")


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
    allow_origins=settings.ALLOWED_ORIGINS if hasattr(settings, 'ALLOWED_ORIGINS') else ["*"],
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
from app.routers import auth, main, teacher, student, api
from app.routers.admin_views import index_router, users_router, subjects_router, exams_router, questions_router, misc_router

app.include_router(main.router)
app.include_router(auth.router, prefix="/auth", tags=["认证"])
app.include_router(index_router, prefix="/admin", tags=["admin"])
app.include_router(users_router, prefix="/admin", tags=["admin-users"])
app.include_router(subjects_router, prefix="/admin", tags=["admin-subjects"])
app.include_router(exams_router, prefix="/admin", tags=["admin-exams"])
app.include_router(questions_router, prefix="/admin", tags=["admin-questions"])
app.include_router(misc_router, prefix="/admin", tags=["admin-misc"])
app.include_router(teacher.router, prefix="/teacher", tags=["教师"])
app.include_router(student.router, prefix="/student", tags=["学生"])
app.include_router(api.router, prefix="/api", tags=["API"])


# 全局异常处理
@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """通用异常处理"""
    error_logger = get_logger("error")
    import traceback
    error_logger.exception(f"未处理的异常 | 请求: {request.url.path} | 错误: {str(exc)}")
    return templates.TemplateResponse(
        "error.html",
        {"request": request, "error": str(exc)},
        status_code=500
    )


# 服务层异常处理
from app.services.exceptions import AppException as AppSvcException

@app.exception_handler(AppSvcException)
async def app_exception_handler(request: Request, exc: AppSvcException):
    """服务层异常处理"""
    from fastapi import status
    code = getattr(exc, 'code', 'APP_ERROR')
    status_code = status.HTTP_400_BAD_REQUEST
    if code == "NOT_FOUND":
        status_code = status.HTTP_404_NOT_FOUND
    elif code == "PERMISSION_DENIED":
        status_code = status.HTTP_403_FORBIDDEN
    return {"success": False, "message": exc.message, "code": code}


# 401 认证失败处理
from fastapi import status


@app.get("/api/health", tags=["系统"])
async def health_check():
    """系统健康检查"""
    return JSONResponse({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "4.0.0"
    })


@app.exception_handler(status.HTTP_401_UNAUTHORIZED)
async def http_unauthorized_handler(request: Request, exc):
    """HTTP 401 认证失败 - 显示认证失败页面"""
    return templates.TemplateResponse(
        "auth/auth_failed.html",
        {
            "request": request,
            "message": exc.detail if hasattr(exc, 'detail') else "认证失败，请重新登录",
            "next": str(request.url) if request.url else None
        },
        status_code=401
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )
