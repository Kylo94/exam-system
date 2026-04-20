"""
REST API 路由
"""
from fastapi import APIRouter, Depends, HTTPException, Request, Form
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from pathlib import Path

from app.auth import get_current_user, require_admin, require_teacher
from app.models.user import User
from app.models.exam import Exam
from app.models.question import Question
from app.models.subject import Subject
from app.models.level import Level
from app.models.knowledge_point import KnowledgePoint
from app.models.submission import Submission
from app.models.answer import Answer

router = APIRouter()


# ===== 文件服务 API =====
@router.get("/uploads/{filename:path}")
async def serve_upload(filename: str):
    """服务上传的图片文件"""
    import logging
    import os
    logger = logging.getLogger(__name__)
    logger.info(f"[serve_upload] Requested: {filename}")
    logger.info(f"[serve_upload] CWD: {os.getcwd()}")

    file_path = Path("uploads") / filename
    logger.info(f"[serve_upload] Full path: {file_path.absolute()}, exists: {file_path.exists()}")

    if not file_path.exists():
        logger.warning(f"[serve_upload] File not found: {file_path}")
        raise HTTPException(status_code=404, detail="文件不存在")

    # Determine content type
    import mimetypes
    content_type, _ = mimetypes.guess_type(str(file_path))
    if content_type is None:
        content_type = "application/octet-stream"

    return FileResponse(file_path, media_type=content_type)


# ===== 科目 API =====
@router.get("/subjects")
async def list_subjects():
    """获取科目列表"""
    subjects = await Subject.all().prefetch_related("levels")
    result = []
    for s in subjects:
        levels = await Level.filter(subject_id=s.id)
        result.append({
            "id": s.id,
            "name": s.name,
            "description": s.description,
            "levels": [{"id": l.id, "name": l.name, "description": l.description} for l in levels]
        })
    return {"success": True, "data": result}


@router.get("/subjects/{subject_id}")
async def get_subject(subject_id: int):
    """获取科目详情"""
    subject = await Subject.get_or_none(id=subject_id)
    if not subject:
        raise HTTPException(status_code=404, detail="科目不存在")

    levels = await Level.filter(subject_id=subject_id).order_by("id")
    return {
        "id": subject.id,
        "name": subject.name,
        "description": subject.description,
        "levels": [{"id": l.id, "name": l.name, "description": l.description} for l in levels]
    }


@router.post("/subjects")
async def create_subject_api(
    name: str,
    description: str = None,
    level_count: int = 3,
    current_user: User = Depends(require_admin)
):
    """创建科目"""
    subject = await Subject.create(name=name, description=description)

    # 自动创建等级
    for i in range(1, level_count + 1):
        level_name = f"第{i}级"
        await Level.create(name=level_name, description=f"{level_name}难度", subject=subject)

    return {"success": True, "data": {"id": subject.id, "name": subject.name}}


@router.put("/subjects/{subject_id}")
async def update_subject_api(
    subject_id: int,
    name: str,
    description: str = None,
    current_user: User = Depends(require_admin)
):
    """更新科目"""
    subject = await Subject.get_or_none(id=subject_id)
    if not subject:
        raise HTTPException(status_code=404, detail="科目不存在")
    subject.name = name
    subject.description = description
    await subject.save()
    return {"success": True, "data": {"id": subject.id, "name": subject.name}}


@router.delete("/subjects/{subject_id}")
async def delete_subject_api(subject_id: int, current_user: User = Depends(require_admin)):
    """删除科目"""
    subject = await Subject.get_or_none(id=subject_id)
    if not subject:
        raise HTTPException(status_code=404, detail="科目不存在")
    await subject.delete()
    return {"success": True}


@router.post("/subjects/{subject_id}/levels")
async def create_level_for_subject_api(
    subject_id: int,
    name: str,
    description: str = None,
    current_user: User = Depends(require_admin)
):
    """为科目创建难度等级"""
    subject = await Subject.get_or_none(id=subject_id)
    if not subject:
        raise HTTPException(status_code=404, detail="科目不存在")

    level = await Level.create(name=name, description=description, subject=subject)
    return {"success": True, "data": {"id": level.id, "name": level.name}}


# ===== 难度等级 API =====
@router.get("/levels")
async def list_levels(subject_id: Optional[int] = None):
    """获取难度等级列表"""
    query = Level.all()
    if subject_id:
        query = query.filter(subject_id=subject_id)
    levels = await query
    return {"success": True, "data": levels}


@router.put("/levels/{level_id}")
async def update_level_api(
    level_id: int,
    name: str,
    description: str = None,
    current_user: User = Depends(require_admin)
):
    """更新难度等级"""
    level = await Level.get_or_none(id=level_id)
    if not level:
        raise HTTPException(status_code=404, detail="等级不存在")
    level.name = name
    level.description = description
    await level.save()
    return {"success": True, "data": {"id": level.id, "name": level.name}}


@router.delete("/levels/{level_id}")
async def delete_level_api(level_id: int, current_user: User = Depends(require_admin)):
    """删除难度等级"""
    level = await Level.get_or_none(id=level_id)
    if not level:
        raise HTTPException(status_code=404, detail="等级不存在")
    await level.delete()
    return {"success": True}


# ===== 知识点 API =====
@router.get("/knowledge-points")
async def list_knowledge_points(subject_id: Optional[int] = None):
    """获取知识点列表"""
    query = KnowledgePoint.all()
    if subject_id:
        query = query.filter(subject_id=subject_id)
    kps = await query.prefetch_related("subject", "level")
    return {"success": True, "data": kps}


@router.get("/knowledge-points/{kp_id}")
async def get_knowledge_point(kp_id: int):
    """获取知识点详情"""
    kp = await KnowledgePoint.get_or_none(id=kp_id).prefetch_related("subject", "level")
    if not kp:
        raise HTTPException(status_code=404, detail="知识点不存在")
    return {"success": True, "data": kp}


@router.post("/knowledge-points")
async def create_knowledge_point(
    name: str,
    subject_id: int,
    level_id: int = None,
    description: str = None,
    current_user: User = Depends(require_admin)
):
    """创建知识点"""
    kp = await KnowledgePoint.create(
        name=name,
        subject_id=subject_id,
        level_id=level_id,
        description=description
    )
    return {"success": True, "data": {"id": kp.id, "name": kp.name}}


@router.put("/knowledge-points/{kp_id}")
async def update_knowledge_point(
    kp_id: int,
    name: str,
    subject_id: int,
    level_id: int = None,
    description: str = None,
    current_user: User = Depends(require_admin)
):
    """更新知识点"""
    kp = await KnowledgePoint.get_or_none(id=kp_id)
    if not kp:
        raise HTTPException(status_code=404, detail="知识点不存在")
    kp.name = name
    kp.subject_id = subject_id
    kp.level_id = level_id
    kp.description = description
    await kp.save()
    return {"success": True}


@router.delete("/knowledge-points/{kp_id}")
async def delete_knowledge_point(kp_id: int, current_user: User = Depends(require_admin)):
    """删除知识点"""
    kp = await KnowledgePoint.get_or_none(id=kp_id)
    if not kp:
        raise HTTPException(status_code=404, detail="知识点不存在")
    await kp.delete()
    return {"success": True}


# ===== 试卷 API =====
@router.get("/exams")
async def list_exams(
    subject_id: Optional[int] = None,
    is_published: Optional[bool] = None
):
    """获取试卷列表"""
    query = Exam.all()
    
    if subject_id:
        query = query.filter(subject_id=subject_id)
    if is_published is not None:
        query = query.filter(is_published=is_published)
    
    exams = await query.prefetch_related("subject", "level")
    return {"success": True, "data": exams}


@router.get("/exams/{exam_id}")
async def get_exam(exam_id: int):
    """获取试卷详情"""
    exam = await Exam.get_or_none(id=exam_id).prefetch_related("questions", "subject", "level")
    if not exam:
        raise HTTPException(status_code=404, detail="试卷不存在")
    return {"success": True, "data": exam}


@router.post("/exams")
async def create_exam_api(
    title: str,
    subject_id: int,
    level_id: int = None,
    total_points: int = 100,
    duration_minutes: int = 60,
    pass_score: int = 60,
    description: str = None,
    current_user: User = Depends(require_teacher)
):
    """创建试卷"""
    exam = await Exam.create(
        title=title,
        subject_id=subject_id,
        level_id=level_id,
        creator=current_user,
        total_points=total_points,
        duration_minutes=duration_minutes,
        pass_score=pass_score,
        description=description,
    )
    return {"success": True, "data": {"id": exam.id}}


@router.put("/exams/{exam_id}")
async def update_exam_api(
    exam_id: int,
    title: str = None,
    is_published: bool = None,
    duration_minutes: int = None,
    pass_score: int = None,
    current_user: User = Depends(require_teacher)
):
    """更新试卷"""
    exam = await Exam.get_or_none(id=exam_id)
    if not exam:
        raise HTTPException(status_code=404, detail="试卷不存在")

    if title:
        exam.title = title
    if is_published is not None:
        exam.is_published = is_published
    if duration_minutes:
        exam.duration_minutes = duration_minutes
    if pass_score:
        exam.pass_score = pass_score

    await exam.save()
    return {"success": True}


@router.delete("/exams/{exam_id}")
async def delete_exam_api(exam_id: int, current_user: User = Depends(require_admin)):
    """删除试卷"""
    exam = await Exam.get_or_none(id=exam_id)
    if not exam:
        raise HTTPException(status_code=404, detail="试卷不存在")

    await exam.delete()
    return {"success": True}


# ===== 题目 API =====
@router.get("/exams/{exam_id}/questions")
async def list_questions(exam_id: int):
    """获取试卷题目列表"""
    questions = await Question.filter(exam_id=exam_id).order_by("order_num")
    return {"success": True, "data": questions}


@router.post("/exams/{exam_id}/questions")
async def create_question_api(
    exam_id: int,
    type: str,
    content: str,
    correct_answer: str,
    points: int = 10,
    options: str = None,
    explanation: str = None,
    knowledge_point_id: int = None,
    difficulty: int = 1,
    current_user: User = Depends(require_teacher)
):
    """创建题目"""
    import json
    
    exam = await Exam.get_or_none(id=exam_id)
    if not exam:
        raise HTTPException(status_code=404, detail="试卷不存在")
    
    options_dict = json.loads(options) if options else {}
    
    question = await Question.create(
        exam=exam,
        type=type,
        content=content,
        correct_answer=correct_answer,
        points=points,
        options=options_dict,
        explanation=explanation,
        knowledge_point_id=knowledge_point_id,
        difficulty=difficulty,
    )
    
    return {"success": True, "data": {"id": question.id}}


@router.put("/questions/{question_id}")
async def update_question_api(
    question_id: int,
    content: str = None,
    correct_answer: str = None,
    points: int = None,
    options: str = None,
    current_user: User = Depends(require_teacher)
):
    """更新题目"""
    import json
    
    question = await Question.get_or_none(id=question_id)
    if not question:
        raise HTTPException(status_code=404, detail="题目不存在")
    
    if content:
        question.content = content
    if correct_answer:
        question.correct_answer = correct_answer
    if points:
        question.points = points
    if options:
        question.options = json.loads(options)
    
    await question.save()
    return {"success": True}


@router.delete("/questions/{question_id}")
async def delete_question_api(question_id: int, current_user: User = Depends(require_teacher)):
    """删除题目"""
    question = await Question.get_or_none(id=question_id)
    if not question:
        raise HTTPException(status_code=404, detail="题目不存在")
    await question.delete()
    return {"success": True}


# ===== 提交记录 API =====
@router.get("/submissions")
async def list_submissions_api(
    exam_id: Optional[int] = None,
    user_id: Optional[int] = None,
    current_user: User = Depends(get_current_user)
):
    """获取提交记录列表"""
    query = Submission.all()
    
    if exam_id:
        query = query.filter(exam_id=exam_id)
    
    if current_user.is_student:
        query = query.filter(user_id=current_user.id)
    elif user_id:
        query = query.filter(user_id=user_id)
    
    submissions = await query.prefetch_related("user", "exam").order_by("-created_at")
    return {"success": True, "data": submissions}


# ===== 用户 API =====
@router.get("/users/me")
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """获取当前用户信息"""
    return {
        "success": True,
        "data": {
            "id": current_user.id,
            "username": current_user.username,
            "email": current_user.email,
            "role": current_user.role,
            "is_active": current_user.is_active,
        }
    }


@router.get("/users/{user_id}")
async def get_user_info(user_id: int, current_user: User = Depends(require_teacher)):
    """获取用户信息"""
    user = await User.get_or_none(id=user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    return {
        "success": True,
        "data": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "role": user.role,
            "is_active": user.is_active,
        }
    }


# ===== AI配置 API =====
@router.get("/ai-configs")
async def list_ai_configs(current_user: User = Depends(get_current_user)):
    """获取AI配置列表"""
    from app.models.ai_config import AIConfig
    configs = await AIConfig.all().prefetch_related("creator")
    return {"success": True, "data": configs}


@router.post("/ai-configs")
async def create_ai_config(
    name: str = Form(...),
    provider: str = Form(...),
    model: str = Form(...),
    api_key: str = Form(...),
    api_url: str = Form(None),
    is_active: bool = Form(True),
    is_default: bool = Form(False),
    current_user: User = Depends(require_admin)
):
    """创建AI配置"""
    from app.models.ai_config import AIConfig

    if is_default:
        await AIConfig.all().update(is_default=False)

    config = await AIConfig.create(
        name=name,
        provider=provider,
        model=model,
        api_key=api_key,
        base_url=api_url if api_url else None,
        is_active=is_active,
        is_default=is_default,
        creator=current_user
    )
    return {"success": True, "data": {"id": config.id}}


@router.delete("/ai-configs/{config_id}")
async def delete_ai_config(config_id: int, current_user: User = Depends(require_admin)):
    """删除AI配置"""
    from app.models.ai_config import AIConfig
    config = await AIConfig.get_or_none(id=config_id)
    if not config:
        raise HTTPException(status_code=404, detail="配置不存在")
    await config.delete()
    return {"success": True}


@router.get("/ai-configs/{config_id}")
async def get_ai_config(config_id: int, current_user: User = Depends(require_admin)):
    """获取单个AI配置"""
    from app.models.ai_config import AIConfig
    config = await AIConfig.get_or_none(id=config_id)
    if not config:
        raise HTTPException(status_code=404, detail="配置不存在")
    return {
        "success": True,
        "data": {
            "id": config.id,
            "name": config.name,
            "provider": config.provider,
            "model": config.model,
            "api_key": config.api_key,
            "base_url": config.base_url,
            "is_active": config.is_active,
            "is_default": config.is_default,
        }
    }


@router.put("/ai-configs/{config_id}")
async def update_ai_config(
    config_id: int,
    name: str = Form(...),
    provider: str = Form(...),
    model: str = Form(...),
    api_key: str = Form(...),
    api_url: str = Form(None),
    is_active: bool = Form(True),
    is_default: bool = Form(False),
    current_user: User = Depends(require_admin)
):
    """更新AI配置"""
    from app.models.ai_config import AIConfig

    config = await AIConfig.get_or_none(id=config_id)
    if not config:
        raise HTTPException(status_code=404, detail="配置不存在")

    if is_default:
        await AIConfig.exclude(id=config_id).update(is_default=False)

    config.name = name
    config.provider = provider
    config.model = model
    config.api_key = api_key
    config.base_url = api_url if api_url else None
    config.is_active = is_active
    config.is_default = is_default
    await config.save()

    return {"success": True}


@router.post("/ai-configs/{config_id}/test")
async def test_ai_config(config_id: int, current_user: User = Depends(require_admin)):
    """测试AI配置连接"""
    from app.models.ai_config import AIConfig
    from app.ai.llm_service import LLMService

    config = await AIConfig.get_or_none(id=config_id)
    if not config:
        raise HTTPException(status_code=404, detail="配置不存在")

    try:
        service = LLMService(provider=config.provider)
        service.config = {
            'api_key': config.api_key,
            'base_url': config.base_url
        }
        service._provider_instance = None  # 强制重新初始化

        result = service.generate_answer("Hello, please respond with 'OK' if you receive this message.")
        return {"success": True, "message": result[:100]}
    except Exception as e:
        return {"success": False, "message": str(e)}
