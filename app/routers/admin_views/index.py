"""管理员 - 首页"""
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse

from app.auth import require_admin
from app.models.exam import Exam
from app.models.knowledge_point import KnowledgePoint
from app.models.question import Question
from app.models.subject import Subject
from app.models.submission import Submission
from app.models.user import User
from app.templating import templates

router = APIRouter()


@router.get("", response_class=HTMLResponse)
async def admin_index(request: Request, current_user: User = Depends(require_admin)):
    """管理员首页"""
    # 并行执行所有统计查询
    import asyncio
    results = await asyncio.gather(
        User.all().count(),
        Subject.all().count(),
        Exam.all().count(),
        Question.all().count(),
        Submission.all().count(),
        KnowledgePoint.all().count(),
    )

    stats = {
        "total_users": results[0] or 0,
        "total_subjects": results[1] or 0,
        "total_exams": results[2] or 0,
        "total_questions": results[3] or 0,
        "total_submissions": results[4] or 0,
        "total_knowledge_points": results[5] or 0,
    }
    return templates.TemplateResponse("admin/index.html", {
        "request": request,
        "current_user": current_user,
        "stats": stats,
    })
