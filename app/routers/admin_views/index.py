"""管理员 - 首页"""
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse

from app.auth import require_admin
from app.models.user import User
from app.models.exam import Exam
from app.models.question import Question
from app.models.subject import Subject
from app.models.knowledge_point import KnowledgePoint
from app.models.submission import Submission
from app.templating import templates

router = APIRouter()


@router.get("", response_class=HTMLResponse)
async def admin_index(request: Request, current_user: User = Depends(require_admin)):
    """管理员首页"""
    stats = {
        "total_users": await User.all().count(),
        "total_subjects": await Subject.all().count(),
        "total_exams": await Exam.all().count(),
        "total_questions": await Question.all().count(),
        "total_submissions": await Submission.all().count(),
        "total_knowledge_points": await KnowledgePoint.all().count(),
    }
    return templates.TemplateResponse("admin/index.html", {
        "request": request,
        "current_user": current_user,
        "stats": stats,
    })
