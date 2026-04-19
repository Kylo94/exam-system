"""
管理员路由
"""
from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import HTMLResponse
from tortoise.queryset import Q

from app.auth import get_current_user, require_admin
from app.models.user import User
from app.models.exam import Exam
from app.models.subject import Subject
from app.models.level import Level
from app.models.knowledge_point import KnowledgePoint
from app.models.submission import Submission
from app.models.teacher_bind_request import TeacherBindRequest
from app.templating import templates

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def admin_home(request: Request, current_user: User = Depends(require_admin)):
    """管理员首页"""
    return templates.TemplateResponse("admin/index.html", {
        "request": request,
        "user": current_user
    })


# ===== 用户管理 =====
@router.get("/users", response_class=HTMLResponse)
async def admin_users(request: Request, current_user: User = Depends(require_admin)):
    """用户列表"""
    users = await User.all().order_by("-created_at")
    return templates.TemplateResponse("admin/users.html", {
        "request": request,
        "user": current_user,
        "users": users
    })


@router.post("/users/{user_id}/toggle-active")
async def toggle_user_active(user_id: int, current_user: User = Depends(require_admin)):
    """切换用户激活状态"""
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="不能禁用自己")
    
    user = await User.get_or_none(id=user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    user.is_active = not user.is_active
    await user.save()
    
    return {"success": True, "is_active": user.is_active}


@router.post("/users/{user_id}/change-role")
async def change_user_role(user_id: int, role: str, current_user: User = Depends(require_admin)):
    """修改用户角色"""
    if role not in ["admin", "teacher", "student"]:
        raise HTTPException(status_code=400, detail="无效的角色")
    
    user = await User.get_or_none(id=user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    user.role = role
    await user.save()
    
    return {"success": True}


# ===== 科目管理 =====
@router.get("/subjects", response_class=HTMLResponse)
async def admin_subjects(request: Request, current_user: User = Depends(require_admin)):
    """科目列表"""
    subjects = await Subject.all().order_by("name")
    return templates.TemplateResponse("admin/subjects.html", {
        "request": request,
        "user": current_user,
        "subjects": subjects
    })


@router.post("/subjects")
async def create_subject(name: str, description: str = None, current_user: User = Depends(require_admin)):
    """创建科目"""
    subject = await Subject.create(name=name, description=description)
    return {"success": True, "id": subject.id}


@router.put("/subjects/{subject_id}")
async def update_subject(subject_id: int, name: str, description: str = None, current_user: User = Depends(require_admin)):
    """更新科目"""
    subject = await Subject.get_or_none(id=subject_id)
    if not subject:
        raise HTTPException(status_code=404, detail="科目不存在")
    
    subject.name = name
    subject.description = description
    await subject.save()
    
    return {"success": True}


@router.delete("/subjects/{subject_id}")
async def delete_subject(subject_id: int, current_user: User = Depends(require_admin)):
    """删除科目"""
    subject = await Subject.get_or_none(id=subject_id)
    if not subject:
        raise HTTPException(status_code=404, detail="科目不存在")
    
    await subject.delete()
    return {"success": True}


# ===== 难度等级管理 =====
@router.get("/levels", response_class=HTMLResponse)
async def admin_levels(request: Request, current_user: User = Depends(require_admin)):
    """难度等级列表"""
    levels = await Level.all().order_by("name")
    return templates.TemplateResponse("admin/levels.html", {
        "request": request,
        "user": current_user,
        "levels": levels
    })


@router.post("/levels")
async def create_level(name: str, description: str = None, current_user: User = Depends(require_admin)):
    """创建难度等级"""
    level = await Level.create(name=name, description=description)
    return {"success": True, "id": level.id}


@router.delete("/levels/{level_id}")
async def delete_level(level_id: int, current_user: User = Depends(require_admin)):
    """删除难度等级"""
    level = await Level.get_or_none(id=level_id)
    if not level:
        raise HTTPException(status_code=404, detail="等级不存在")
    
    await level.delete()
    return {"success": True}


# ===== 知识点管理 =====
@router.get("/knowledge-points", response_class=HTMLResponse)
async def admin_knowledge_points(request: Request, current_user: User = Depends(require_admin)):
    """知识点列表"""
    kps = await KnowledgePoint.all().prefetch_related("subject", "level").order_by("subject__name", "name")
    subjects = await Subject.all()
    levels = await Level.all()
    
    return templates.TemplateResponse("admin/knowledge_points.html", {
        "request": request,
        "user": current_user,
        "knowledge_points": kps,
        "subjects": subjects,
        "levels": levels
    })


# ===== 试卷管理 =====
@router.get("/exams", response_class=HTMLResponse)
async def admin_exams(request: Request, current_user: User = Depends(require_admin)):
    """试卷列表"""
    exams = await Exam.all().prefetch_related("subject", "level", "creator").order_by("-created_at")
    return templates.TemplateResponse("admin/exams.html", {
        "request": request,
        "user": current_user,
        "exams": exams
    })


# ===== 绑定申请管理 =====
@router.get("/bind-requests", response_class=HTMLResponse)
async def admin_bind_requests(request: Request, current_user: User = Depends(require_admin)):
    """学生绑定申请列表"""
    requests = await TeacherBindRequest.all().prefetch_related("student", "teacher").order_by("-created_at")
    return templates.TemplateResponse("admin/bind_requests.html", {
        "request": request,
        "user": current_user,
        "bind_requests": requests
    })


@router.post("/bind-requests/{request_id}/approve")
async def approve_bind_request(request_id: int, current_user: User = Depends(require_admin)):
    """批准绑定申请"""
    bind_request = await TeacherBindRequest.get_or_none(id=request_id)
    if not bind_request:
        raise HTTPException(status_code=404, detail="申请不存在")
    
    student = await User.get_or_none(id=bind_request.student_id)
    if student:
        student.teacher_id = bind_request.teacher_id
        await student.save()
    
    bind_request.status = "approved"
    await bind_request.save()
    
    return {"success": True}


@router.post("/bind-requests/{request_id}/reject")
async def reject_bind_request(request_id: int, current_user: User = Depends(require_admin)):
    """拒绝绑定申请"""
    bind_request = await TeacherBindRequest.get_or_none(id=request_id)
    if not bind_request:
        raise HTTPException(status_code=404, detail="申请不存在")
    
    bind_request.status = "rejected"
    await bind_request.save()
    
    return {"success": True}


# ===== 统计报表 =====
@router.get("/statistics", response_class=HTMLResponse)
async def admin_statistics(request: Request, current_user: User = Depends(require_admin)):
    """统计报表"""
    total_users = await User.all().count()
    total_exams = await Exam.all().count()
    total_submissions = await Submission.all().count()
    graded_submissions = await Submission.filter(status="graded").count()

    return templates.TemplateResponse("admin/statistics.html", {
        "request": request,
        "user": current_user,
        "stats": {
            "total_users": total_users,
            "total_exams": total_exams,
            "total_submissions": total_submissions,
            "graded_submissions": graded_submissions,
        }
    })


# ===== AI配置管理 =====
@router.get("/ai-configs", response_class=HTMLResponse)
async def admin_ai_configs(request: Request, current_user: User = Depends(require_admin)):
    """AI配置列表"""
    from app.models.ai_config import AIConfig
    ai_configs = await AIConfig.all().prefetch_related("creator").order_by("-created_at")

    return templates.TemplateResponse("ai_configs.html", {
        "request": request,
        "user": current_user,
        "ai_configs": ai_configs,
        "is_admin_view": True
    })
