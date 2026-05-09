"""管理员 - 题目管理"""
import json
import logging
import os
import tempfile
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, StreamingResponse

from app.ai.llm_service import LLMService
from app.auth import require_admin
from app.models.audit_log import AuditLog
from app.models.exam import Exam
from app.models.knowledge_point import KnowledgePoint
from app.models.question import Question
from app.models.subject import Subject
from app.models.user import User
from app.services.knowledge_point_service import KnowledgePointService
from app.services.question_service import QuestionService
from app.templating import templates

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/questions", response_class=HTMLResponse)
async def admin_questions_page(
    request: Request,
    current_user: User = Depends(require_admin)
):
    """题目管理页面"""
    exams = await Exam.all().prefetch_related("subject").order_by("-id")
    subjects = await Subject.all().order_by("name")

    question_types = [
        {"value": "single_choice", "label": "单选题"},
        {"value": "multiple_choice", "label": "多选题"},
        {"value": "true_false", "label": "判断题"},
        {"value": "fill_blank", "label": "填空题"},
        {"value": "essay", "label": "简答题"},
    ]

    return templates.TemplateResponse("admin/questions.html", {
        "request": request,
        "current_user": current_user,
        "exams": exams,
        "subjects": subjects,
        "question_types": question_types,
    })


@router.get("/api/exams/{exam_id}/questions")
async def admin_list_questions(exam_id: int, current_user: User = Depends(require_admin)):
    """获取试卷题目列表"""
    questions = await QuestionService.get_questions_by_exam(exam_id)
    result = []
    for q in questions:
        result.append({
            "id": q.id,
            "exam_id": q.exam_id,
            "type": q.type,
            "type_display": q.type_display,
            "content": q.content,
            "options": q.options,
            "correct_answer": q.correct_answer,
            "points": q.points,
            "explanation": q.explanation,
            "difficulty": q.difficulty,
            "order_num": q.order_num,
            "has_image": q.has_image,
            "images": q.images if q.images else [],  # 返回图片数组
            "image_data": q.image_data,  # 兼容旧接口
            "question_metadata": q.question_metadata,
            "knowledge_point": q.knowledge_point.name if q.knowledge_point else None,
            "knowledge_point_id": q.knowledge_point_id,
        })
    return {"success": True, "data": result}


@router.post("/api/exams/{exam_id}/questions")
async def admin_create_question(
    exam_id: int,
    request: Request,
    current_user: User = Depends(require_admin)
):
    """创建题目"""
    body = await request.json()
    client_ip = request.client.host if request.client else None

    try:
        question = await QuestionService.create_question(
            exam_id=exam_id,
            type=body.get('type', 'single_choice'),
            content=body.get('content', ''),
            correct_answer=body.get('correct_answer', ''),
            points=body.get('points', 10),
            options=body.get('options', {}),
            explanation=body.get('explanation'),
            difficulty=body.get('difficulty', 1),
            has_image=body.get('has_image', False),
            image_data=body.get('image_data'),
            question_metadata=body.get('question_metadata', {}),
        )
        # 审计日志
        await AuditLog.log_create(
            user=current_user,
            resource_type="question",
            resource_id=question.id,
            description=f"创建题目: {question.content[:50]}...",
            ip_address=client_ip,
            status="success"
        )
        return {"success": True, "data": {"id": question.id}}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/api/questions/{question_id}")
async def admin_get_question(
    question_id: int,
    current_user: User = Depends(require_admin)
):
    """获取题目详情"""
    try:
        question = await QuestionService.get_question_or_404(question_id)
        return {
            "success": True,
            "data": {
                "id": question.id,
                "exam_id": question.exam_id,
                "type": question.type,
                "content": question.content,
                "options": question.options,
                "correct_answer": question.correct_answer,
                "points": question.points,
                "explanation": question.explanation,
                "difficulty": question.difficulty,
                "order_num": question.order_num,
                "has_image": question.has_image,
                "images": question.images if question.images else [],
                "image_data": question.image_data,
                "question_metadata": question.question_metadata,
            }
        }
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.put("/api/questions/{question_id}")
async def admin_update_question(
    question_id: int,
    request: Request,
    current_user: User = Depends(require_admin)
):
    """更新题目"""
    body = await request.json()
    logger.info(f"[update_question] Request body: {body}")
    client_ip = request.client.host if request.client else None

    try:
        question = await QuestionService.update_question(
            question_id=question_id,
            type=body.get('type'),
            content=body.get('content'),
            correct_answer=body.get('correct_answer'),
            points=body.get('points'),
            options=body.get('options'),
            explanation=body.get('explanation'),
            difficulty=body.get('difficulty'),
            image_data=body.get('image_data'),
            question_metadata=body.get('question_metadata'),
            knowledge_point_id=body.get('knowledge_point_id'),
        )
        logger.info(f"[update_question] Saved. Final images={question.images}")
        # 审计日志
        await AuditLog.log_update(
            user=current_user,
            resource_type="question",
            resource_id=question_id,
            description=f"更新题目: {question.content[:50]}...",
            ip_address=client_ip,
            status="success"
        )
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/api/questions/{question_id}")
async def admin_delete_question(question_id: int, request: Request, current_user: User = Depends(require_admin)):
    """删除题目"""
    client_ip = request.client.host if request.client else None
    try:
        # 获取题目信息用于日志
        question = await QuestionService.get_question_or_404(question_id)
        q_content = question.content[:50] if question.content else f"ID:{question_id}"
        await QuestionService.delete_question(question_id)
        # 审计日志
        await AuditLog.log_delete(
            user=current_user,
            resource_type="question",
            resource_id=question_id,
            description=f"删除题目: {q_content}...",
            ip_address=client_ip,
            status="success"
        )
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/api/questions")
async def admin_list_all_questions(
    exam_id: int = None,
    subject_id: int = None,
    level_id: int = None,
    knowledge_point_id: int = None,
    type: str = None,
    difficulty: int = None,
    has_image: bool = None,
    page: int = 1,
    page_size: int = 50,
    current_user: User = Depends(require_admin)
):
    """获取所有题目列表（支持筛选）"""
    query = Question.all()

    if exam_id:
        query = query.filter(exam_id=exam_id)
    if type:
        query = query.filter(type=type)
    if difficulty:
        query = query.filter(difficulty=difficulty)
    if has_image is not None:
        query = query.filter(has_image=has_image)
    if subject_id:
        query = query.filter(exam__subject_id=subject_id)
    if level_id:
        query = query.filter(exam__level_id=level_id)

    # knowledge_point_id筛选在Python层进行（JSON contains在SQLite不支持）
    # 先获取足够的数据进行筛选和分页
    all_questions = await query.prefetch_related("exam", "knowledge_point").order_by("-id")

    # Python层过滤
    if knowledge_point_id:
        filtered = [q for q in all_questions if q.knowledge_point_ids and knowledge_point_id in q.knowledge_point_ids]
    else:
        filtered = all_questions

    total = len(filtered)
    offset = (page - 1) * page_size
    questions = filtered[offset:offset + page_size]

    # 批量获取知识点信息
    result = []
    for q in questions:
        kp_names = []
        if q.knowledge_point_ids:
            kps = await KnowledgePoint.filter(id__in=q.knowledge_point_ids).all()
            kp_names = [kp.name for kp in kps]

        result.append({
            "id": q.id,
            "exam_id": q.exam_id,
            "exam_title": q.exam.title if q.exam else None,
            "subject_id": q.exam.subject_id if q.exam else None,
            "type": q.type,
            "type_display": q.type_display,
            "content": q.content,
            "options": q.options,
            "correct_answer": q.correct_answer,
            "points": q.points,
            "difficulty": q.difficulty,
            "has_image": q.has_image,
            "images": q.images if q.images else [],
            "image_data": q.image_data,
            "question_metadata": q.question_metadata,
            "knowledge_point": q.knowledge_point.name if q.knowledge_point else None,
            "knowledge_point_ids": q.knowledge_point_ids or [],
            "knowledge_point_names": kp_names,
            "created_at": q.created_at.isoformat() if q.created_at else None,
        })

    return {
        "success": True,
        "data": result,
        "total": total,
        "page": page,
        "page_size": page_size
    }


@router.post("/api/questions/batch-delete")
async def admin_batch_delete_questions(
    request: Request,
    question_ids: list[int],
    current_user: User = Depends(require_admin)
):
    """批量删除题目"""
    client_ip = request.client.host if request.client else None
    deleted = await QuestionService.batch_delete(question_ids)
    # 审计日志
    await AuditLog.log(
        action="batch_delete",
        resource="question",
        user=current_user,
        description=f"批量删除 {deleted} 道题目",
        ip_address=client_ip,
        status="success",
        details={"question_ids": question_ids}
    )
    return {"success": True, "deleted": deleted}


@router.post("/api/questions/assign-knowledge-points")
async def assign_knowledge_points(
    request: Request,
    current_user: User = Depends(require_admin)
):
    """智能分配知识点到指定题目"""
    try:
        body = await request.json()
        question_ids = body.get('question_ids', [])
        ai_config_id = body.get('ai_config_id')

        if not question_ids:
            return {"success": False, "message": "没有选择题目"}

        # 获取题目信息
        questions = await Question.filter(id__in=question_ids).all()
        if not questions:
            return {"success": False, "message": "未找到指定题目"}

        # 获取科目和等级
        exam = await Exam.get_or_none(id=questions[0].exam_id)
        if not exam or not exam.subject_id:
            return {"success": False, "message": "题目未关联试卷或试卷没有科目信息"}

        subject_id = exam.subject_id
        level_id = exam.level_id

        # 获取AI配置
        from app.models.ai_config import AIConfig
        if ai_config_id:
            ai_config = await AIConfig.get_or_none(id=ai_config_id)
        else:
            ai_config = await AIConfig.filter(is_active=True, is_default=True).first()

        if not ai_config:
            return {"success": False, "message": "没有可用的AI配置"}

        # 构建题目列表
        question_list = []
        for q in questions:
            content = q.content[:300] if q.content else ""
            question_list.append({
                "id": q.id,
                "content": content
            })

        # 调用知识点服务进行匹配
        from app.ai.llm_service import LLMService
        llm_service = LLMService(provider=ai_config.provider)
        llm_service.config = {
            'api_key': ai_config.api_key,
            'base_url': ai_config.base_url,
            'model': ai_config.model
        }

        from app.services.knowledge_point_service import KnowledgePointService
        kp_result = await KnowledgePointService.match_and_assign_knowledge_points(
            questions=question_list,
            subject_id=subject_id,
            level_id=level_id,
            llm_service=llm_service
        )

        # 更新题目的知识点
        results = kp_result.get('results', [])
        summary = kp_result.get('summary', {})

        updated_results = []
        for res in results:
            q_id = res.get('question_id')
            kp_ids = res.get('knowledge_point_ids', [])
            kp_names = res.get('knowledge_point_names', [])

            # 更新题目
            if q_id:
                question = next((q for q in questions if q.id == q_id), None)
                if question and kp_ids:
                    question.knowledge_point_ids = kp_ids
                    question.knowledge_point_id = kp_ids[0]
                    await question.save()

            # 构建前端期望的返回格式
            question = next((q for q in questions if q.id == q_id), None)
            result_item = {
                "id": q_id,
                "question_content": question.content[:50] + "..." if question and question.content else f"题目 #{q_id}",
                "status": "assigned" if kp_ids else "no_match",
                "knowledge_point_name": kp_names[0] if kp_names else None,
                "knowledge_point_names": kp_names,
                "confidence": 0.8 if kp_ids else 0,  # 默认置信度
                "reason": res.get('reason', ''),
            }
            updated_results.append(result_item)

        return {
            "success": True,
            "data": {
                "results": updated_results,
                "summary": {
                    "total": len(question_ids),
                    "assigned": summary.get("assigned", 0),
                    "created": summary.get("created", 0),
                    "no_match": summary.get("no_match", 0),
                    "suggest_new": summary.get("created", 0),  # 新建的知识点数量
                }
            }
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"success": False, "message": str(e)}




