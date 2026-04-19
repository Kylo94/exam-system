"""
教师路由
"""
from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import HTMLResponse
from tortoise.queryset import Q

from app.auth import get_current_user, require_teacher
from app.models.user import User
from app.models.exam import Exam
from app.models.question import Question
from app.models.subject import Subject
from app.models.level import Level
from app.models.submission import Submission
from app.models.answer import Answer
from app.templating import templates

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def teacher_home(request: Request, current_user: User = Depends(require_teacher)):
    """教师首页"""
    return templates.TemplateResponse("teacher/index.html", {
        "request": request,
        "user": current_user
    })


# ===== 学生管理 =====
@router.get("/students", response_class=HTMLResponse)
async def teacher_students(request: Request, current_user: User = Depends(require_teacher)):
    """学生列表"""
    students = await User.filter(teacher_id=current_user.id, role="student").order_by("-created_at")

    return templates.TemplateResponse("teacher/students.html", {
        "request": request,
        "user": current_user,
        "students": students
    })


# ===== 我的试卷 =====
@router.get("/exams", response_class=HTMLResponse)
async def teacher_exams(request: Request, current_user: User = Depends(require_teacher)):
    """我的试卷列表"""
    exams = await Exam.filter(creator_id=current_user.id).prefetch_related("subject", "level").order_by("-created_at")

    return templates.TemplateResponse("teacher/exams.html", {
        "request": request,
        "user": current_user,
        "exams": exams
    })


@router.get("/exams/create", response_class=HTMLResponse)
async def create_exam_page(request: Request, current_user: User = Depends(require_teacher)):
    """创建试卷页面"""
    subjects = await Subject.all()
    levels = await Level.all()

    return templates.TemplateResponse("teacher/exam_form.html", {
        "request": request,
        "user": current_user,
        "subjects": subjects,
        "levels": levels,
        "exam": None
    })


@router.get("/exams/{exam_id}/edit", response_class=HTMLResponse)
async def edit_exam_page(exam_id: int, request: Request, current_user: User = Depends(require_teacher)):
    """编辑试卷页面"""
    exam = await Exam.get_or_none(id=exam_id)
    if not exam:
        raise HTTPException(status_code=404, detail="试卷不存在")

    if exam.creator_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权限编辑此试卷")

    subjects = await Subject.all()
    levels = await Level.all()
    questions = await Question.filter(exam_id=exam_id)

    return templates.TemplateResponse("teacher/exam_form.html", {
        "request": request,
        "user": current_user,
        "subjects": subjects,
        "levels": levels,
        "exam": exam,
        "questions": questions
    })


# ===== 成绩查看 =====
@router.get("/submissions", response_class=HTMLResponse)
async def teacher_submissions(request: Request, current_user: User = Depends(require_teacher)):
    """答题记录列表"""
    # 获取自己学生的提交记录
    student_ids = await User.filter(teacher_id=current_user.id).values_list("id", flat=True)
    submissions = await Submission.filter(user_id__in=student_ids).prefetch_related("user", "exam").order_by("-created_at")

    return templates.TemplateResponse("teacher/submissions.html", {
        "request": request,
        "user": current_user,
        "submissions": submissions
    })


@router.get("/submissions/{submission_id}", response_class=HTMLResponse)
async def submission_detail(submission_id: int, request: Request, current_user: User = Depends(require_teacher)):
    """答题详情"""
    submission = await Submission.get_or_none(id=submission_id).prefetch_related("user", "exam", "answers__question")

    if not submission:
        raise HTTPException(status_code=404, detail="提交记录不存在")

    # 检查权限 - 只能查看自己学生的提交
    student = await User.get_or_none(id=submission.user_id)
    if not student or student.teacher_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权限查看此记录")

    return templates.TemplateResponse("teacher/submission_detail.html", {
        "request": request,
        "user": current_user,
        "submission": submission
    })


# ===== AI配置 =====
@router.get("/ai-configs", response_class=HTMLResponse)
async def teacher_ai_configs(request: Request, current_user: User = Depends(require_teacher)):
    """AI配置列表"""
    from app.models.ai_config import AIConfig
    ai_configs = await AIConfig.filter(creator_id=current_user.id).order_by("-created_at")
    
    return templates.TemplateResponse("teacher/ai_configs.html", {
        "request": request,
        "user": current_user,
        "ai_configs": ai_configs
    })
