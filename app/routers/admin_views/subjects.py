"""管理员 - 科目和等级管理"""
import json
import logging

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from tortoise.queryset import Q

from app.auth import require_admin
from app.models.level import Level
from app.models.subject import Subject
from app.models.user import User
from app.services.subject_service import SubjectService
from app.services.knowledge_point_service import KnowledgePointService
from app.templating import templates

router = APIRouter()
logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/subjects", response_class=HTMLResponse)
async def admin_subjects(
    request: Request,
    page: int = 1,
    page_size: int = 20,
    search: str = None,
    current_user: User = Depends(require_admin)
):
    """科目列表"""
    query = Subject.all()

    if search:
        query = query.filter(Q(name__contains=search) | Q(description__contains=search))

    total = await query.count()
    offset = (page - 1) * page_size
    subjects = await query.prefetch_related("levels").order_by("name").offset(offset).limit(page_size)

    total_pages = (total + page_size - 1) // page_size if total > 0 else 1

    return templates.TemplateResponse("admin/subjects.html", {
        "request": request,
        "current_user": current_user,
        "subjects": subjects,
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": total_pages
        },
        "filters": {"search": search}
    })


@router.post("/subjects")
async def create_subject(
    name: str = Form(...),
    description: str = Form(None),
    level_count: int = Form(3),
    current_user: User = Depends(require_admin)
):
    """创建科目"""
    try:
        subject = await SubjectService.create_subject(name, description, level_count)
        return {"success": True, "id": subject.id}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/subjects/{subject_id}/levels")
async def create_level_for_subject(
    subject_id: int,
    name: str,
    description: str = None,
    current_user: User = Depends(require_admin)
):
    """为科目创建难度等级"""
    try:
        level = await SubjectService.create_level(subject_id, name, description)
        return {"success": True, "id": level.id}
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/subjects/{subject_id}")
async def get_subject(subject_id: int, current_user: User = Depends(require_admin)):
    """获取科目详情"""
    try:
        subject = await SubjectService.get_subject_or_404(subject_id)
        levels = await Level.filter(subject_id=subject_id).order_by("id")
        return {
            "id": subject.id,
            "name": subject.name,
            "description": subject.description,
            "levels": [{"id": l.id, "name": l.name, "description": l.description} for l in levels]
        }
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.put("/subjects/{subject_id}")
async def update_subject(
    subject_id: int,
    name: str,
    description: str = None,
    current_user: User = Depends(require_admin)
):
    """更新科目"""
    try:
        await SubjectService.update_subject(subject_id, name, description)
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.put("/levels/{level_id}")
async def update_level(
    level_id: int,
    name: str,
    description: str = None,
    current_user: User = Depends(require_admin)
):
    """更新等级"""
    try:
        await SubjectService.update_level(level_id, name, description)
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/subjects/{subject_id}")
async def delete_subject(subject_id: int, current_user: User = Depends(require_admin)):
    """删除科目（同时删除关联的等级）"""
    try:
        await SubjectService.delete_subject(subject_id)
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/levels/{level_id}")
async def delete_level(level_id: int, current_user: User = Depends(require_admin)):
    """删除难度等级"""
    try:
        await SubjectService.delete_level(level_id)
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


# 独立的等级管理（已废弃，合并到科目管理）
@router.get("/levels", response_class=HTMLResponse)
async def admin_levels_redirect(request: Request, current_user: User = Depends(require_admin)):
    """重定向到科目管理"""
    return RedirectResponse(url="/admin/subjects", status_code=303)


@router.post("/levels")
async def create_level(name: str, description: str = None, current_user: User = Depends(require_admin)):
    """创建难度等级"""
    level = await Level.create(name=name, description=description)
    return {"success": True, "id": level.id}

# 知识点管理
@router.get("/knowledge-points", response_class=HTMLResponse)
async def admin_knowledge_points(
    request: Request,
    page: int = 1,
    page_size: int = 20,
    subject_id: int = None,
    level_id: int = None,
    search: str = None,
    current_user: User = Depends(require_admin)
):
    """知识点管理 - 支持层级导航"""

    # 使用 Service 层获取统计数据
    subjects_with_stats = await SubjectService.get_subjects_with_stats()

    current_subject = None
    current_level = None
    levels = []
    knowledge_points = []

    if subject_id:
        current_subject = await Subject.get_or_none(id=subject_id)
        if current_subject:
            levels = await SubjectService.get_levels_with_stats(subject_id)

            if level_id:
                current_level = await Level.get_or_none(id=level_id)
                if current_level:
                    knowledge_points = await SubjectService.get_knowledge_points_with_stats(level_id)

    total = len(knowledge_points)
    total_pages = (total + page_size - 1) // page_size if total > 0 else 1

    return templates.TemplateResponse("admin/knowledge_points.html", {
        "request": request,
        "current_user": current_user,
        "subjects": subjects_with_stats,
        "current_subject": current_subject,
        "current_level": current_level,
        "levels": levels,
        "knowledge_points": knowledge_points,
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": total_pages
        },
    })


# ===== AI知识点合并 =====
@router.post("/api/knowledge-points/ai-merge")
async def ai_merge_knowledge_points(
    request: Request,
    subject_id: int,
    level_id: int,
    current_user: User = Depends(require_admin)
):
    """AI合并相似知识点（SSE实时进度）"""

    async def event_stream():
        def progress_msg(progress, message, level="info", details=None):
            data = {"progress": progress, "message": message, "level": level}
            if details:
                data["details"] = details
            return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"

        try:
            # 获取AI配置
            from app.models.ai_config import AIConfig
            ai_config = await AIConfig.filter(is_active=True, is_default=True).first()
            if not ai_config:
                yield progress_msg(100, "未找到可用的AI配置", "error")
                return

            from app.ai.llm_service import LLMService
            llm_service = LLMService(provider=ai_config.provider)
            llm_service.config = {
                'api_key': ai_config.api_key,
                'base_url': ai_config.base_url,
                'model': ai_config.model
            }

            yield progress_msg(10, "正在分析知识点相似度...")

            result = await KnowledgePointService.merge_similar_knowledge_points(
                subject_id=subject_id,
                level_id=level_id,
                llm_service=llm_service
            )

            merged = result.get('merged', 0)
            absorbed = result.get('absorbed', [])
            msg = result.get('message', '')

            yield progress_msg(100, msg, "success", {
                "merged": merged,
                "absorbed": absorbed
            })

        except Exception as e:
            logger.exception(f"AI合并知识点失败: {e}")
            yield progress_msg(100, f"合并失败: {str(e)}", "error")

    return StreamingResponse(event_stream(), media_type="text/event-stream")
