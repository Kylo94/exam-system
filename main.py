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
from app.middleware import register_exception_handlers
register_exception_handlers(app)


@app.get("/api/health", tags=["系统"])
async def health_check():
    """系统健康检查"""
    return JSONResponse({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "4.0.0"
    })


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )
