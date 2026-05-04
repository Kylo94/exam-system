"""管理员 - 其他页面"""
import os
from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse

from app.auth import require_admin
from app.models.user import User
from app.models.exam import Exam
from app.models.submission import Submission
from app.models.teacher_bind_request import TeacherBindRequest
from app.models.ai_config import AIConfig
from app.models.audit_log import AuditLog
from app.models.system_settings import SystemSettings
from app.templating import templates, clear_app_name_cache, load_app_name_async
from app.config import settings

router = APIRouter()

# 日志文件映射
LOG_FILES = {
    "app": "app.log",
    "error": "error.log",
    "access": "access.log",
    "ai": "ai.log",
    "knowledge_point": "knowledge_point.log",
}


# API: 更新设置
@router.post("/api/settings")
async def update_settings(
    request: Request,
    category: str = Form(...),
    current_user: User = Depends(require_admin)
):
    """更新设置"""
    form_data = await request.form()

    # 定义各类设置的字段
    setting_fields = {
        "general": ["app_name", "allow_register"],
        "exam": ["exam_default_duration", "exam_default_total_points", "exam_default_pass_score", "submission_max_per_day"],
        "ai": ["ai_enabled", "auto_grade_essay"],
        "security": ["require_email_verification", "token_expire_hours"],
        "logging": ["log_level", "log_backup_count"],
    }

    fields = setting_fields.get(category, [])
    for key in fields:
        value = form_data.get(key)
        if value is not None:
            # 确定值类型
            value_type = "string"
            if key in ["allow_register", "ai_enabled", "auto_grade_essay", "require_email_verification"]:
                value_type = "bool"
            elif key in ["exam_default_duration", "exam_default_total_points", "exam_default_pass_score", "submission_max_per_day", "token_expire_hours", "log_backup_count"]:
                value_type = "int"

            await SystemSettings.set_value(key, value, value_type=value_type, category=category)

            # 如果更新了应用名称，清除并重新加载缓存
            if key == "app_name":
                clear_app_name_cache()
                await load_app_name_async()

    return RedirectResponse(url="/admin/settings?success=1", status_code=303)


# API: 获取日志内容
@router.get("/api/logs/{log_type}")
async def get_log_content(
    log_type: str,
    lines: int = 200,
    current_user: User = Depends(require_admin)
):
    """获取日志文件内容"""
    if log_type not in LOG_FILES:
        return JSONResponse({"success": False, "message": "无效的日志类型"}, status_code=400)

    log_path = os.path.join(settings.LOG_DIR, LOG_FILES[log_type])

    if not os.path.exists(log_path):
        return JSONResponse({"success": True, "content": "", "message": "日志文件不存在"})

    try:
        with open(log_path, 'r', encoding='utf-8') as f:
            all_lines = f.readlines()
            # 获取最后N行
            content = ''.join(all_lines[-lines:])
        return JSONResponse({"success": True, "content": content})
    except Exception as e:
        return JSONResponse({"success": False, "message": str(e)}, status_code=500)


# API: 清空日志文件
@router.delete("/api/logs/{log_type}")
async def clear_log_file(
    log_type: str,
    current_user: User = Depends(require_admin)
):
    """清空日志文件"""
    if log_type not in LOG_FILES:
        return JSONResponse({"success": False, "message": "无效的日志类型"}, status_code=400)

    log_path = os.path.join(settings.LOG_DIR, LOG_FILES[log_type])

    if not os.path.exists(log_path):
        return JSONResponse({"success": True, "message": "日志文件不存在"})

    try:
        with open(log_path, 'w', encoding='utf-8') as f:
            f.write("")
        return JSONResponse({"success": True, "message": "日志已清空"})
    except Exception as e:
        return JSONResponse({"success": False, "message": str(e)}, status_code=500)


@router.get("/bind-requests", response_class=HTMLResponse)
async def admin_bind_requests(request: Request, current_user: User = Depends(require_admin)):
    """绑定申请列表"""
    bind_requests = await TeacherBindRequest.all().prefetch_related("student", "teacher").order_by("-created_at")
    return templates.TemplateResponse("admin/bind_requests.html", {
        "request": request,
        "current_user": current_user,
        "bind_requests": bind_requests
    })


@router.post("/bind-requests/{request_id}/approve")
async def approve_bind_request(request_id: int, current_user: User = Depends(require_admin)):
    """批准绑定申请"""
    from fastapi import HTTPException
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
    from fastapi import HTTPException
    bind_request = await TeacherBindRequest.get_or_none(id=request_id)
    if not bind_request:
        raise HTTPException(status_code=404, detail="申请不存在")

    bind_request.status = "rejected"
    await bind_request.save()

    return {"success": True}


@router.get("/submissions", response_class=HTMLResponse)
async def admin_submissions(
    request: Request,
    page: int = 1,
    page_size: int = 20,
    current_user: User = Depends(require_admin)
):
    """答题记录列表"""
    query = Submission.all().prefetch_related("user", "exam")
    total = await query.count()
    offset = (page - 1) * page_size
    submissions = await query.order_by("-created_at").offset(offset).limit(page_size)
    total_pages = (total + page_size - 1) // page_size if total > 0 else 1

    return templates.TemplateResponse("admin/submissions.html", {
        "request": request,
        "current_user": current_user,
        "submissions": submissions,
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": total_pages
        }
    })


@router.get("/ai-configs", response_class=HTMLResponse)
async def admin_ai_configs(request: Request, current_user: User = Depends(require_admin)):
    """AI配置列表"""
    ai_configs = await AIConfig.all().prefetch_related("creator").order_by("-created_at")
    return templates.TemplateResponse("ai_configs.html", {
        "request": request,
        "current_user": current_user,
        "ai_configs": ai_configs,
        "is_admin_view": True
    })


@router.get("/settings", response_class=HTMLResponse)
async def admin_settings(request: Request, current_user: User = Depends(require_admin)):
    """系统设置"""
    from app.models.system_settings import SystemSettings
    from app.config import settings

    # 确保默认设置存在
    await SystemSettings.initialize_defaults()

    # 获取所有设置
    all_settings = await SystemSettings.all()
    settings_dict = {s.key: s.value for s in all_settings}

    # 获取AI配置列表
    ai_configs = await AIConfig.all().prefetch_related("creator").order_by("-created_at")

    return templates.TemplateResponse("admin/settings.html", {
        "request": request,
        "current_user": current_user,
        # 基本设置
        "system_name": settings_dict.get("app_name", settings.APP_NAME),
        "allow_register": settings_dict.get("allow_register", "true"),
        # 考试设置
        "exam_default_duration": settings_dict.get("exam_default_duration", "60"),
        "exam_default_total_points": settings_dict.get("exam_default_total_points", "100"),
        "exam_default_pass_score": settings_dict.get("exam_default_pass_score", "60"),
        "submission_max_per_day": settings_dict.get("submission_max_per_day", "10"),
        # AI设置
        "ai_enabled": settings_dict.get("ai_enabled", "true"),
        "auto_grade_essay": settings_dict.get("auto_grade_essay", "false"),
        "ai_configs": ai_configs,
        # 安全设置
        "require_email_verification": settings_dict.get("require_email_verification", "false"),
        # 日志设置
        "log_level": settings_dict.get("log_level", settings.LOG_LEVEL),
        "log_backup_count": settings_dict.get("log_backup_count", str(settings.LOG_BACKUP_COUNT)),
    })


@router.get("/audit-logs", response_class=HTMLResponse)
async def admin_audit_logs(
    request: Request,
    page: int = 1,
    page_size: int = 50,
    current_user: User = Depends(require_admin)
):
    """审计日志"""
    query = AuditLog.all()
    total = await query.count()
    offset = (page - 1) * page_size
    logs = await query.order_by("-created_at").offset(offset).limit(page_size)
    total_pages = (total + page_size - 1) // page_size if total > 0 else 1

    return templates.TemplateResponse("admin/audit_logs.html", {
        "request": request,
        "current_user": current_user,
        "logs": logs,
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": total_pages
        }
    })


@router.get("/statistics", response_class=HTMLResponse)
async def admin_statistics(request: Request, current_user: User = Depends(require_admin)):
    """统计报表"""
    total_users = await User.all().count()
    total_exams = await Exam.all().count()
    total_submissions = await Submission.all().count()
    graded_submissions = await Submission.filter(status="graded").count()

    return templates.TemplateResponse("admin/statistics.html", {
        "request": request,
        "current_user": current_user,
        "stats": {
            "total_users": total_users,
            "total_exams": total_exams,
            "total_submissions": total_submissions,
            "graded_submissions": graded_submissions,
        }
    })
