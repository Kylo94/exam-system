"""
主页路由
"""
from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse
from tortoise.queryset import Q

from app.auth import get_current_user, get_optional_current_user
from app.models.user import User
from app.models.exam import Exam
from app.models.submission import Submission
from app.templating import templates

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def home(request: Request, current_user: User = Depends(get_optional_current_user)):
    """首页"""
    return templates.TemplateResponse("index.html", {"request": request, "current_user": current_user})


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, current_user: User = Depends(get_current_user)):
    """仪表盘"""
    context = {"request": request, "current_user": current_user}
    
    if current_user.is_admin:
        # 管理员仪表盘
        from app.models.user import User
        from app.models.exam import Exam
        from app.models.submission import Submission
        
        context["stats"] = {
            "total_users": await User.all().count(),
            "total_exams": await Exam.all().count(),
            "total_submissions": await Submission.all().count(),
        }
        return templates.TemplateResponse("admin/index.html", context)
    
    elif current_user.is_teacher:
        # 教师仪表盘
        students_count = await User.filter(teacher_id=current_user.id).count()
        exams_created = await Exam.filter(creator_id=current_user.id).count()
        submissions_count = await Submission.all().count()
        
        context["stats"] = {
            "students_count": students_count,
            "exams_created": exams_created,
            "submissions_count": submissions_count,
        }
        return templates.TemplateResponse("teacher/dashboard.html", context)
    
    else:
        # 学生仪表盘
        recent_exams = await Exam.filter(is_published=True).order_by("-created_at").limit(5).prefetch_related("subject")
        my_submissions = await Submission.filter(user_id=current_user.id).order_by("-created_at").limit(5)
        
        context["recent_exams"] = recent_exams
        context["my_submissions"] = my_submissions
        return templates.TemplateResponse("student/dashboard.html", context)


@router.get("/exam/{exam_id}", response_class=HTMLResponse)
async def exam_detail(request: Request, exam_id: int, current_user: User = Depends(get_current_user)):
    """试卷详情"""
    exam = await Exam.get_or_none(id=exam_id).prefetch_related("subject", "level", "creator", "questions")
    
    if not exam:
        raise HTTPException(status_code=404, detail="试卷不存在")
    
    # 检查是否已开始答题
    submission = None
    if current_user.is_student:
        submission = await Submission.filter(
            exam_id=exam_id,
            user_id=current_user.id
        ).first()
    
    return templates.TemplateResponse("exam/detail.html", {
        "request": request,
        "current_user": current_user,
        "exam": exam,
        "submission": submission,
    })


@router.get("/exam/{exam_id}/start", response_class=HTMLResponse)
async def start_exam(request: Request, exam_id: int, current_user: User = Depends(get_current_user)):
    """开始答题"""
    if not current_user.is_student:
        raise HTTPException(status_code=403, detail="只有学生可以答题")
    
    exam = await Exam.get_or_none(id=exam_id).prefetch_related("questions")
    
    if not exam:
        raise HTTPException(status_code=404, detail="试卷不存在")

    # 创建答题记录
    submission = await Submission.create(
        exam=exam,
        user=current_user,
        status="in_progress",
        total_score=exam.total_points,
        started_at=datetime.now(),
    )
    
    return templates.TemplateResponse("exam/take.html", {
        "request": request,
        "current_user": current_user,
        "exam": exam,
        "submission": submission,
        "questions": exam.questions,
    })


from datetime import datetime
