"""管理员路由子模块导出"""
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse

from app.auth import require_admin
from app.models.user import User
from app.models.exam import Exam
from app.models.subject import Subject
from app.models.level import Level
from app.templating import templates

router = APIRouter()

# 导出子路由
from app.routers.admin_views.users import router as users_router
from app.routers.admin_views.subjects import router as subjects_router
from app.routers.admin_views.exams import router as exams_router
from app.routers.admin_views.questions import router as questions_router

__all__ = ["users_router", "subjects_router", "exams_router", "questions_router"]


@router.get("/", response_class=HTMLResponse)
async def admin_home(request: Request, current_user: User = Depends(require_admin)):
    """管理员首页"""
    total_users = await User.all().count()
    total_exams = await Exam.all().count()
    total_subjects = await Subject.all().count()
    total_levels = await Level.all().count()

    return templates.TemplateResponse("admin/index.html", {
        "request": request,
        "current_user": current_user,
        "stats": {
            "total_users": total_users,
            "total_exams": total_exams,
            "total_subjects": total_subjects,
            "total_levels": total_levels,
        }
    })