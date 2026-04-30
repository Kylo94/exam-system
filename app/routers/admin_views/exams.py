"""管理员 - 试卷管理"""
from fastapi import APIRouter, Depends, Request, HTTPException, Form, Body
from fastapi.responses import HTMLResponse
from tortoise.queryset import Q

from app.auth import require_admin
from app.models.user import User
from app.models.subject import Subject
from app.models.level import Level
from app.models.question import Question
from app.services.exam_service import ExamService
from app.templating import templates

router = APIRouter()


@router.get("/exams", response_class=HTMLResponse)
async def admin_exams(
    request: Request,
    page: int = 1,
    page_size: int = 20,
    subject_id: int = None,
    level_id: int = None,
    status: str = None,
    search: str = None,
    current_user: User = Depends(require_admin)
):
    """试卷列表"""
    from app.models.exam import Exam
    query = Exam.all()

    if subject_id:
        query = query.filter(subject_id=subject_id)
    if level_id:
        query = query.filter(level_id=level_id)
    if status == "published":
        query = query.filter(is_published=True)
    elif status == "draft":
        query = query.filter(is_published=False)
    if search:
        query = query.filter(Q(title__contains=search))

    total = await query.count()
    offset = (page - 1) * page_size
    exams = await query.prefetch_related("subject", "level", "creator").order_by("-created_at").offset(offset).limit(page_size)
    subjects = await Subject.all()
    levels = await Level.all()

    total_pages = (total + page_size - 1) // page_size if total > 0 else 1

    return templates.TemplateResponse("admin/exams.html", {
        "request": request,
        "current_user": current_user,
        "exams": exams,
        "subjects": subjects,
        "levels": levels,
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": total_pages
        },
        "filters": {"subject_id": subject_id, "level_id": level_id, "status": status, "search": search}
    })


@router.get("/api/exams/{exam_id}")
async def get_exam_admin(exam_id: int, current_user: User = Depends(require_admin)):
    """获取试卷详情"""
    try:
        exam = await ExamService.get_exam_or_404(exam_id)
        return {
            "success": True,
            "data": {
                "id": exam.id,
                "title": exam.title,
                "subject_id": exam.subject_id,
                "level_id": exam.level_id,
                "duration_minutes": exam.duration_minutes,
                "total_points": exam.total_points,
                "pass_score": exam.pass_score,
                "is_published": exam.is_published,
                "is_active": exam.is_published,
            }
        }
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.put("/api/exams/{exam_id}")
async def update_exam_admin(
    exam_id: int,
    request: Request,
    current_user: User = Depends(require_admin)
):
    """更新试卷"""
    body = await request.json()

    try:
        exam = await ExamService.update_exam(
            exam_id=exam_id,
            title=body.get('title'),
            subject_id=body.get('subject_id'),
            level_id=body.get('level_id'),
            duration_minutes=body.get('duration_minutes'),
            total_points=body.get('total_points'),
            pass_score=body.get('pass_score'),
            is_published=body.get('is_published'),
        )
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/api/exams")
async def create_exam_admin(
    title: str = Form(...),
    subject_id: int = Form(...),
    level_id: int = Form(None),
    duration_minutes: int = Form(60),
    total_points: int = Form(100),
    pass_score: int = Form(60),
    is_published: bool = Form(False),
    current_user: User = Depends(require_admin)
):
    """创建试卷"""
    try:
        exam = await ExamService.create_exam(
            title=title,
            subject_id=subject_id,
            level_id=level_id,
            creator=current_user,
            duration_minutes=duration_minutes,
            total_points=total_points,
            pass_score=pass_score,
            is_published=is_published,
        )
        return {"success": True, "data": {"id": exam.id}}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/api/exams/batch-delete")
async def admin_batch_delete_exams(
    exam_ids: list[int],
    current_user: User = Depends(require_admin)
):
    """批量删除试卷"""
    deleted = await ExamService.batch_delete(exam_ids)
    return {"success": True, "deleted": deleted}


@router.post("/api/exams/batch-publish")
async def admin_batch_publish_exams(
    exam_ids: list[int],
    is_published: bool = True,
    current_user: User = Depends(require_admin)
):
    """批量发布/取消发布试卷"""
    updated = await ExamService.batch_publish(exam_ids, is_published)
    return {"success": True, "updated": updated}


@router.get("/exams/{exam_id}/edit", response_class=HTMLResponse)
async def admin_edit_exam_page(exam_id: int, request: Request, current_user: User = Depends(require_admin)):
    """编辑试卷页面"""
    try:
        exam = await ExamService.get_exam_or_404(exam_id)
    except Exception:
        raise HTTPException(status_code=404, detail="试卷不存在")

    subjects = await Subject.all()
    levels = await Level.all()
    questions = await Question.filter(exam_id=exam_id).order_by("order_num")

    return templates.TemplateResponse("exam_edit.html", {
        "request": request,
        "current_user": current_user,
        "subjects": subjects,
        "levels": levels,
        "exam": exam,
        "questions": questions,
        "is_admin": True
    })