"""管理员 - 题目管理"""
import json
import logging
import os
import tempfile
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse

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


@router.post("/api/upload-image")
async def admin_upload_image(
    file: UploadFile = File(...),
    current_user: User = Depends(require_admin)
):
    """上传图片"""
    allowed_types = {'image/jpeg', 'image/png', 'image/gif', 'image/webp'}
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="不支持的图片格式")

    ext = Path(file.filename).suffix.lower()
    filename = f"{uuid.uuid4().hex}{ext}"
    upload_dir = Path("uploads/images")
    upload_dir.mkdir(parents=True, exist_ok=True)

    file_path = upload_dir / filename

    content = await file.read()
    import aiofiles
    async with aiofiles.open(file_path, 'wb') as f:
        await f.write(content)

    relative_path = f"images/{filename}"
    return {"success": True, "data": {"path": relative_path}}


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



@router.get("/api/uploads/{filename:path}")
async def serve_upload(filename: str):
    """服务上传的图片文件"""
    file_path = Path("uploads") / filename

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="文件不存在")

    return FileResponse(file_path)


@router.post("/api/upload/parse/preview")
async def parse_upload_file_preview(
    request: Request,
    file: UploadFile = File(...),
    title: str = Form(...),
    subject_id: str = Form(...),
    level_id: str = Form(None),
    parse_method: str = Form("ai"),
    ai_config_id: int = Form(None),
    current_user: User = Depends(require_admin)
):
    """解析文件并返回JSON预览（不保存到数据库）"""
    import tempfile

    file_content = await file.read()
    filename = file.filename

    try:
        subject_id_int = int(subject_id) if subject_id else None
        level_id_int = int(level_id) if level_id else None
    except (ValueError, TypeError):
        subject_id_int = None
        level_id_int = None

    use_ai_parsing = parse_method == "ai" and ai_config_id

    ai_config_obj = None
    if use_ai_parsing:
        from app.models.ai_config import AIConfig
        ai_config_obj = await AIConfig.get_or_none(id=ai_config_id)

    # 步骤1: 提取文本和图片
    from app.parsers.docx_extractor import DocxExtractor
    extractor = DocxExtractor(upload_folder='uploads/images')
    try:
        suffix = Path(filename).suffix.lower()
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(file_content)
            tmp_path = tmp.name
        raw_text, image_info = extractor.extract_text_and_images(tmp_path)
    except Exception as e:
        return {"success": False, "message": f"文本提取失败: {str(e)}"}
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)

    # 步骤2: 本地规则拆分题目
    from app.parsers.rule_parser import RuleParser
    rule_parser = RuleParser()
    local_questions = rule_parser.parse(raw_text, image_info)

    if not local_questions:
        return {"success": False, "message": "未发现任何题目"}

    questions_data = local_questions

    # 步骤3: 批量AI处理（仅预览）
    if use_ai_parsing and ai_config_obj:
        from app.parsers.ai_parser import AIParser
        try:
            ai_parser = AIParser(ai_config=ai_config_obj)
            enhanced_questions = ai_parser.batch_enhance_questions(questions_data, image_info)
            questions_data = enhanced_questions
        except Exception as e:
            return {"success": False, "message": f"AI处理失败: {str(e)}"}

    # 步骤4: 获取已有知识点列表作为提示（预览时不进行AI匹配，保存时再匹配）
    existing_kps = []
    if level_id_int and subject_id_int:
        from app.models.knowledge_point import KnowledgePoint
        existing_kps = await KnowledgePoint.filter(subject_id=subject_id_int, level_id=level_id_int).all()
        kp_suggestions = [kp.name for kp in existing_kps[:20]]  # 只显示前20个作为提示

    # 构建预览数据
    preview_data = {
        "exam_title": title,
        "subject_id": subject_id_int,
        "level_id": level_id_int,
        "total_questions": len(questions_data),
        "suggested_knowledge_points": kp_suggestions,  # 已有知识点列表作为提示
        "questions": []
    }

    # 预览时不匹配知识点，保存时再进行知识点匹配和创建

    for idx, q in enumerate(questions_data):
        preview_data["questions"].append({
            "index": idx + 1,
            "type": q.get('type', 'unknown'),
            "content": q.get('content', ''),
            "options": q.get('options', {}),
            "correct_answer": q.get('correct_answer', ''),
            "points": q.get('points', 10),
            "difficulty": q.get('difficulty', 1),
            "explanation": q.get('explanation', ''),
            "knowledge_point_names": [],  # 预览时为空，保存时会匹配
            "images": q.get('images', []),  # 图片列表
            "question_metadata": q.get('question_metadata', {}),  # 元数据（包含选项图片）
        })

    return {"success": True, "data": preview_data}


@router.post("/api/upload/parse/stream")
async def parse_upload_file_stream(
    request: Request,
    file: UploadFile = File(...),
    title: str = Form(...),
    subject_id: str = Form(...),
    level_id: str = Form(None),
    parse_method: str = Form("ai"),
    ai_config_id: int = Form(None),
    duration_minutes: int = Form(60),
    total_points: int = Form(100),
    pass_score: int = Form(60),
    is_published: bool = Form(False),
    current_user: User = Depends(require_admin)
):
    """解析上传的文件并创建试卷（支持SSE实时进度和取消）"""
    task_id = str(uuid.uuid4())[:8]
    file_content = await file.read()
    filename = file.filename

    try:
        subject_id_int = int(subject_id) if subject_id else None
    except (ValueError, TypeError):
        subject_id_int = None
    try:
        level_id_int = int(level_id) if level_id else None
    except (ValueError, TypeError):
        level_id_int = None

    from asyncio import Event

    from app import tasks
    cancel_event = Event()
    tasks.CANCEL_EVENTS[task_id] = cancel_event

    async def event_stream():
        def progress_msg(progress, message='', level='info', current=0, total=0, details=None):
            data = {
                'progress': progress,
                'message': message,
                'level': level,
                'task_id': task_id,
                'current': current,
                'total': total
            }
            if details:
                data['details'] = details
            return f"data: {json.dumps(data)}\n\n"

        tmp_path = None
        exam_id = None
        try:
            suffix = Path(filename).suffix.lower()
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                tmp.write(file_content)
                tmp_path = tmp.name

            yield progress_msg(0, f'📤 文件上传完成: {filename}', level='info', current=0, total=0)

            exam = await Exam.create(
                title=title,
                subject_id=subject_id_int,
                level_id=level_id_int,
                creator=current_user,
                duration_minutes=duration_minutes,
                total_points=total_points,
                pass_score=pass_score,
                is_published=is_published,
            )
            exam_id = exam.id

            yield progress_msg(5, f'✅ 试卷创建成功 (ID: {exam.id})', level='success', current=0, total=0)

            questions_data = []
            use_ai_parsing = parse_method == "ai" and ai_config_id

            ai_config_obj = None
            if use_ai_parsing:
                from app.models.ai_config import AIConfig
                ai_config_obj = await AIConfig.get_or_none(id=ai_config_id)
                if not ai_config_obj:
                    yield progress_msg(8, f'⚠️ 未找到 AI 配置(id={ai_config_id})，改为本地解析...', level='warning')
                    use_ai_parsing = False
                else:
                    yield progress_msg(8, f'🤖 使用AI配置: {ai_config_obj.name} ({ai_config_obj.provider} - {ai_config_obj.model})', level='info')
            else:
                yield progress_msg(8, f'📝 使用本地规则解析 (parse_method={parse_method}, ai_config_id={ai_config_id})', level='info')

            # 步骤1: 本地提取文本和图片
            yield progress_msg(5, '📝 正在提取文档文本和图片...', level='info')
            from app.parsers.docx_extractor import DocxExtractor
            extractor = DocxExtractor(upload_folder='uploads/images')
            try:
                raw_text, image_info = extractor.extract_text_and_images(tmp_path)
                yield progress_msg(10, f'✅ 文本提取完成 ({len(raw_text)}字符, {len(image_info)}张图片)', level='success')
            except Exception as e:
                yield progress_msg(100, f'❌ 文本提取失败: {str(e)[:50]}', level='error')
                return

            # 步骤2: 本地规则拆分题目
            yield progress_msg(15, '🔍 正在用规则拆分题目...', level='info')
            from app.parsers.rule_parser import RuleParser
            rule_parser = RuleParser()
            local_questions = rule_parser.parse(raw_text, image_info)
            yield progress_msg(20, f'📋 规则拆分完成，发现 {len(local_questions)} 道题目', level='success', current=0, total=len(local_questions))

            if not local_questions:
                yield progress_msg(100, '❌ 未发现任何题目', level='error')
                return

            questions_data = local_questions

            if not questions_data:
                yield progress_msg(100, '❌ 未发现任何题目，解析失败', level='error', current=0, total=0)
                return

            # 步骤3: 批量AI处理
            total = len(questions_data)
            ai_results = questions_data
            kp_assignments = {}  # question_id -> list of kp_ids

            if not use_ai_parsing or not ai_config_obj:
                yield progress_msg(25, '📝 跳过AI处理，直接保存题目到数据库', level='info')
            else:
                yield progress_msg(25, f'🤖 开始批量AI处理 ({total}道题目，一次性处理)', level='info', current=0, total=total)

                from app.parsers.ai_parser import AIParser
                try:
                    ai_parser = AIParser(ai_config=ai_config_obj)
                    yield progress_msg(30, '🤖 AI处理中...', level='info')

                    enhanced_questions = ai_parser.batch_enhance_questions(questions_data, image_info)

                    ai_results = enhanced_questions
                    yield progress_msg(60, f'✅ AI批量处理完成，{len(enhanced_questions)}道题目已增强', level='success', current=total, total=total)

                    # 步骤3.5: 批量知识点匹配
                    if level_id_int and subject_id_int:
                        yield progress_msg(65, '🏷️ 开始智能匹配知识点...', level='info')

                        from app.services.knowledge_point_service import KnowledgePointService
                        try:
                            llm_service = LLMService(provider=ai_config_obj.provider)
                            llm_service.config = {
                                'api_key': ai_config_obj.api_key,
                                'base_url': ai_config_obj.base_url,
                                'model': ai_config_obj.model
                            }

                            # 构建题目列表
                            question_list = []
                            for idx, q in enumerate(ai_results):
                                question_list.append({
                                    "id": idx + 1,
                                    "content": q.get('content', '')
                                })

                            kp_result = await KnowledgePointService.match_and_assign_knowledge_points(
                                questions=question_list,
                                subject_id=subject_id_int,
                                level_id=level_id_int,
                                llm_service=llm_service
                            )

                            # 转换结果：idx -> question_id -> kp_ids
                            for res in kp_result.get('results', []):
                                q_id = res.get('question_id')
                                kp_ids = res.get('knowledge_point_ids', [])
                                if q_id and kp_ids:
                                    kp_assignments[q_id] = kp_ids

                            summary_kp = kp_result.get('summary', {})
                            yield progress_msg(
                                70,
                                f'🏷️ 知识点匹配完成：已分配{summary_kp.get("assigned", 0)}个，新建{summary_kp.get("created", 0)}个',
                                level='success'
                            )
                        except Exception as kp_err:
                            yield progress_msg(70, f'⚠️ 知识点匹配失败: {str(kp_err)[:50]}，跳过', level='warning')
                    else:
                        yield progress_msg(70, '⚠️ 未指定科目/等级，跳过知识点匹配', level='warning')

                except Exception as e:
                    yield progress_msg(50, f'⚠️ AI处理失败: {str(e)[:50]}，使用本地解析结果', level='warning')
                    ai_results = questions_data

            # 步骤4: 逐题创建到数据库
            if cancel_event.is_set():
                yield progress_msg(95, '⚠️ 用户取消，删除已创建的试卷...', level='warning')
                if exam_id:
                    try:
                        exam = await Exam.get_or_none(id=exam_id)
                        if exam:
                            await exam.delete()
                            yield progress_msg(100, '🗑️ 试卷已删除', level='info')
                    except Exception as del_exam_error:
                        yield progress_msg(100, f'⚠️ 删除试卷失败: {str(del_exam_error)}', level='error')
                return

            yield progress_msg(95, '💾 开始保存题目到数据库...', level='info')

            created_count = 0
            failed_count = 0

            for idx, q_data in enumerate(questions_data):
                if cancel_event.is_set():
                    yield progress_msg(95, '⚠️ 用户取消，停止保存...', level='warning')
                    if exam_id:
                        try:
                            exam = await Exam.get_or_none(id=exam_id)
                            if exam:
                                await exam.delete()
                                yield progress_msg(100, f'🗑️ 已删除试卷 (ID: {exam_id})', level='info')
                        except Exception as del_exam_error:
                            yield progress_msg(100, f'⚠️ 删除试卷失败: {str(del_exam_error)}', level='error')
                    return

                final_data = ai_results[idx] if ai_results[idx] else q_data

                q_type = final_data.get('type', 'unknown')
                q_type_display = {
                    'single_choice': '单选题', 'multiple_choice': '多选题',
                    'true_false': '判断题', 'fill_blank': '填空题',
                    'short_answer': '简答题', 'coding': '编程题'
                }.get(q_type, q_type)
                q_content_preview = (final_data.get('content', '')[:40] + '...') if len(final_data.get('content', '')) > 40 else final_data.get('content', '')

                try:
                    images = final_data.get('images', [])
                    if not isinstance(images, list):
                        images = [images] if images else []

                    # 转换options格式：list转dict
                    options = final_data.get('options', {})
                    if isinstance(options, list):
                        options = {opt.get('id', chr(65+i)): opt.get('text', '') for i, opt in enumerate(options)}

                    # 获取知识点IDs
                    q_idx = idx + 1
                    q_kp_ids = kp_assignments.get(q_idx, [])

                    _question = await Question.create(
                        exam=exam,
                        type=final_data.get('type', 'choice') or 'choice',
                        content=final_data.get('content') or '题目内容',
                        options=options,
                        correct_answer=final_data.get('correct_answer') or '',
                        points=final_data.get('points') or 10,
                        difficulty=final_data.get('difficulty') or 1,
                        images=images,
                        question_metadata=final_data.get('question_metadata', {}),
                        order_num=idx + 1,
                        knowledge_point_ids=q_kp_ids,
                        # 如果有知识点且没有主知识点，设置第一个为默认
                        knowledge_point_id=q_kp_ids[0] if q_kp_ids else None,
                    )
                    created_count += 1

                    yield progress_msg(
                        95 + int((idx + 1) / total * 5),
                        f'✅ 第{idx+1}题已保存' + (f' (分配{len(q_kp_ids)}个知识点)' if q_kp_ids else ''),
                        level='success',
                        current=idx + 1,
                        total=total,
                        details=[f'[{idx+1}/{total}] ✅ {q_type_display}: {q_content_preview} - 已保存']
                    )

                except Exception:
                    failed_count += 1
                    yield progress_msg(
                        95 + int((idx + 1) / total * 5),
                        f'❌ 第{idx+1}题保存失败',
                        level='error',
                        current=idx + 1,
                        total=total
                    )

            if created_count > 0:
                yield progress_msg(100, f'🎉 完成！成功创建 {created_count} 道题目' + (f'，失败 {failed_count} 道' if failed_count > 0 else ''), 'success', current=created_count, total=total)
            else:
                yield progress_msg(100, '❌ 创建失败，未成功创建任何题目', 'error', current=0, total=total)

            result_data = json.dumps({
                'success': created_count > 0,
                'data': {
                    'exam_id': exam.id,
                    'questions': {
                        'created': created_count,
                        'failed': failed_count,
                        'total': total
                    }
                },
                'progress': 100
            })
            yield f"data: {result_data}\n\n"

        except Exception as e:
            if cancel_event.is_set() and exam_id:
                try:
                    exam = await Exam.get_or_none(id=exam_id)
                    if exam:
                        await exam.delete()
                except:
                    pass
            error_data = json.dumps({
                'success': False,
                'message': str(e),
                'progress': 0,
                'task_id': task_id
            })
            yield f"data: {error_data}\n\n"
        finally:
            tasks.CANCEL_EVENTS.pop(task_id, None)
            if tmp_path and os.path.exists(tmp_path):
                os.unlink(tmp_path)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


@router.post("/api/upload/parse/save")
async def parse_upload_file_save(
    request: Request,
    current_user: User = Depends(require_admin)
):
    """保存预览的JSON数据到数据库（保存时进行知识点匹配）"""
    try:
        body = await request.json()
        preview_data = body.get('data')
    except Exception as e:
        return {"success": False, "message": f"JSON解析失败: {str(e)}"}

    if not preview_data:
        return {"success": False, "message": "没有可保存的数据"}

    exam_title = preview_data.get('exam_title', '未命名试卷')
    subject_id = preview_data.get('subject_id')
    level_id = preview_data.get('level_id')
    questions = preview_data.get('questions', [])

    print(f"[DEBUG] 保存请求: title={exam_title}, subject_id={subject_id}, level_id={level_id}, questions_count={len(questions)}")

    if not questions:
        return {"success": False, "message": "没有题目可保存"}

    if not subject_id:
        return {"success": False, "message": "缺少科目信息"}

    try:
        # 创建试卷
        exam = await Exam.create(
            title=exam_title,
            subject_id=subject_id,
            level_id=level_id,
            creator=current_user,
            duration_minutes=60,
            total_points=100,
            pass_score=60,
            is_published=False,
        )
        print(f"[DEBUG] 试卷创建成功: exam_id={exam.id}")
    except Exception as e:
        print(f"[ERROR] 创建试卷失败: {e}")
        import traceback
        traceback.print_exc()
        return {"success": False, "message": f"创建试卷失败: {str(e)}"}

    created_count = 0
    failed_count = 0
    kp_created_count = 0

    # 准备题目列表用于知识点匹配
    question_list = [{"id": idx + 1, "content": q.get('content', '')[:300]} for idx, q in enumerate(questions)]

    # 进行知识点匹配（使用AI）
    kp_result_map = {}  # question_id -> [kp_names]
    kp_name_to_obj = {}  # kp_name -> KnowledgePoint

    # 如果有level_id，进行知识点匹配
    if level_id:
        try:
            from app.models.ai_config import AIConfig
            # 获取默认AI配置
            ai_config = await AIConfig.filter(is_active=True, is_default=True).first()
            if ai_config:
                from app.ai.llm_service import LLMService
                llm_service = LLMService(provider=ai_config.provider)
                llm_service.config = {
                    'api_key': ai_config.api_key,
                    'base_url': ai_config.base_url,
                    'model': ai_config.model
                }

                kp_result = await KnowledgePointService.match_and_assign_knowledge_points(
                    questions=question_list,
                    subject_id=subject_id,
                    level_id=level_id,
                    llm_service=llm_service
                )

                for res in kp_result.get('results', []):
                    q_id = res.get('question_id')
                    kp_names = res.get('knowledge_point_names', [])
                    if q_id and kp_names:
                        kp_result_map[q_id] = kp_names
                        # 创建或获取知识点
                        for kp_name in kp_names:
                            if kp_name not in kp_name_to_obj:
                                kp = await KnowledgePointService.get_or_create_knowledge_point(
                                    subject_id=subject_id,
                                    level_id=level_id,
                                    name=kp_name,
                                    description="自动创建"
                                )
                                kp_name_to_obj[kp_name] = kp
                                kp_created_count += 1
        except Exception as e:
            print(f"[ERROR] 知识点匹配失败: {e}")
            import traceback
            traceback.print_exc()

    # 创建题目
    for idx, q in enumerate(questions):
        q_idx = idx + 1
        kp_names = kp_result_map.get(q_idx, q.get('knowledge_point_names', []))
        kp_ids = [kp_name_to_obj[kp_name].id for kp_name in kp_names if kp_name in kp_name_to_obj]

        # 转换options格式：list转dict
        options = q.get('options', {})
        if isinstance(options, list):
            options = {opt.get('id', chr(65+i)): opt.get('text', '') for i, opt in enumerate(options)}

        # 获取图片和元数据
        images = q.get('images', [])
        if images and not isinstance(images, list):
            images = [images]
        question_metadata = q.get('question_metadata', {})

        try:
            await Question.create(
                exam=exam,
                type=q.get('type', 'choice') or 'choice',
                content=q.get('content', '题目内容'),
                options=options,
                correct_answer=q.get('correct_answer', ''),
                points=q.get('points', 10),
                difficulty=q.get('difficulty', 1),
                explanation=q.get('explanation'),
                knowledge_point_ids=kp_ids,
                knowledge_point_id=kp_ids[0] if kp_ids else None,
                order_num=q.get('index', idx + 1),
                images=images,
                question_metadata=question_metadata,
            )
            created_count += 1
        except Exception as e:
            print(f"[ERROR] 创建题目失败: {e}")
            import traceback
            traceback.print_exc()
            failed_count += 1

    return {
        "success": True,
        "data": {
            "exam_id": exam.id,
            "questions": {
                "created": created_count,
                "failed": failed_count,
                "total": len(questions)
            },
            "knowledge_points_created": kp_created_count
        }
    }


@router.post("/api/upload/batch/stream")
async def batch_upload_stream(
    request: Request,
    current_user: User = Depends(require_admin)
):
    """批量上传并解析文件（SSE实时进度，不需要确认）"""
    import base64
    import tempfile

    from app.parsers.ai_parser import AIParser
    from app.parsers.docx_extractor import DocxExtractor
    from app.parsers.rule_parser import RuleParser
    from app.services.knowledge_point_service import KnowledgePointService

    task_id = str(uuid.uuid4())[:8]
    body = await request.json()

    files_meta = body.get('files', [])
    files_data = body.get('file_data', [])
    parse_method = body.get('parse_method', 'local')
    ai_config_id = body.get('ai_config_id')
    is_published = body.get('is_published', False)

    # 构建文件映射
    file_map = {f['name']: f for f in files_meta}

    ai_config_obj = None
    if parse_method == 'ai' and ai_config_id:
        from app.models.ai_config import AIConfig
        ai_config_obj = await AIConfig.get_or_none(id=ai_config_id)

    from asyncio import Event

    from app import tasks
    cancel_event = Event()
    tasks.CANCEL_EVENTS[task_id] = cancel_event

    async def event_stream():
        def progress_msg(progress, message='', level='info', current=0, total=0):
            data = {
                'progress': progress,
                'message': message,
                'level': level,
                'task_id': task_id,
                'current': current,
                'total': total
            }
            return f"data: {json.dumps(data)}\n\n"

        total_files = len(files_meta)
        total_questions = 0
        total_created = 0
        total_failed = 0

        try:
            yield progress_msg(0, f'📤 开始批量处理 {total_files} 个文件...', level='info', current=0, total=total_files)

            for file_idx, file_data in enumerate(files_data):
                if cancel_event.is_set():
                    yield progress_msg(90, '⚠️ 用户取消，停止处理', level='warning')
                    break

                filename = file_data['name']
                meta = file_map.get(filename, {})
                title = meta.get('title', os.path.splitext(filename)[0])
                subject_id = meta.get('subject_id')
                level_id = meta.get('level_id')

                yield progress_msg(
                    int(file_idx / total_files * 100),
                    f'📄 处理文件 {file_idx + 1}/{total_files}: {filename}',
                    level='info',
                    current=file_idx + 1,
                    total=total_files
                )

                # 解码文件
                try:
                    file_content = base64.b64decode(file_data['data'])
                except Exception:
                    yield progress_msg(
                        int(file_idx / total_files * 100),
                        f'❌ 文件解码失败: {filename}',
                        level='error',
                        current=file_idx + 1,
                        total=total_files
                    )
                    continue

                # 保存临时文件
                suffix = Path(filename).suffix.lower()
                tmp_path = None
                try:
                    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                        tmp.write(file_content)
                        tmp_path = tmp.name

                    # 提取文本和图片
                    extractor = DocxExtractor(upload_folder='uploads/images')
                    raw_text, image_info = extractor.extract_text_and_images(tmp_path)

                    # 规则拆分题目
                    rule_parser = RuleParser()
                    questions_data = rule_parser.parse(raw_text, image_info)

                    if not questions_data:
                        yield progress_msg(
                            int((file_idx + 0.5) / total_files * 100),
                            f'⚠️ 未发现题目: {filename}',
                            level='warning',
                            current=file_idx + 1,
                            total=total_files
                        )
                        continue

                    # AI增强
                    if parse_method == 'ai' and ai_config_obj:
                        try:
                            ai_parser = AIParser(ai_config=ai_config_obj)
                            questions_data = ai_parser.batch_enhance_questions(questions_data, image_info)
                        except Exception as e:
                            yield progress_msg(
                                int((file_idx + 0.5) / total_files * 100),
                                f'⚠️ AI增强失败: {str(e)[:30]}，使用本地结果',
                                level='warning'
                            )

                    # 知识点匹配
                    kp_assignments = {}
                    if level_id and subject_id and parse_method == 'ai' and ai_config_obj:
                        try:
                            llm_service = LLMService(provider=ai_config_obj.provider)
                            llm_service.config = {
                                'api_key': ai_config_obj.api_key,
                                'base_url': ai_config_obj.base_url,
                                'model': ai_config_obj.model
                            }
                            question_list = [{"id": idx + 1, "content": q.get('content', '')} for idx, q in enumerate(questions_data)]
                            kp_result = await KnowledgePointService.match_and_assign_knowledge_points(
                                questions=question_list,
                                subject_id=subject_id,
                                level_id=level_id,
                                llm_service=llm_service
                            )
                            for res in kp_result.get('results', []):
                                q_id = res.get('question_id')
                                kp_ids = res.get('knowledge_point_ids', [])
                                if q_id and kp_ids:
                                    kp_assignments[q_id] = kp_ids
                        except Exception as e:
                            yield progress_msg(0, f'⚠️ 知识点匹配失败: {str(e)[:30]}', level='warning')

                    # 创建试卷
                    exam = await Exam.create(
                        title=title,
                        subject_id=subject_id,
                        level_id=level_id,
                        creator=current_user,
                        is_published=is_published,
                    )

                    # 保存题目
                    created = 0
                    failed = 0
                    for idx, q_data in enumerate(questions_data):
                        q_kp_ids = kp_assignments.get(idx + 1, [])
                        try:
                            await Question.create(
                                exam=exam,
                                type=q_data.get('type', 'choice') or 'choice',
                                content=q_data.get('content', '题目内容'),
                                options=q_data.get('options', {}),
                                correct_answer=q_data.get('correct_answer', ''),
                                points=q_data.get('points', 10),
                                difficulty=q_data.get('difficulty', 1),
                                explanation=q_data.get('explanation'),
                                knowledge_point_ids=q_kp_ids,
                                knowledge_point_id=q_kp_ids[0] if q_kp_ids else None,
                                order_num=idx + 1,
                            )
                            created += 1
                        except Exception:
                            failed += 1

                    total_created += created
                    total_failed += failed
                    total_questions += len(questions_data)

                    yield progress_msg(
                        int((file_idx + 1) / total_files * 100),
                        f'✅ {filename}: 创建 {created} 道题目',
                        level='success',
                        current=file_idx + 1,
                        total=total_files
                    )

                finally:
                    if tmp_path and os.path.exists(tmp_path):
                        os.unlink(tmp_path)

            yield progress_msg(
                100,
                f'🎉 完成！共处理 {total_files} 个文件，{total_created} 道题目',
                level='success',
                current=total_files,
                total=total_files
            )
            result_data = json.dumps({
                'success': True,
                'data': {
                    'total_files': total_files,
                    'total_questions': total_questions,
                    'created': total_created,
                    'failed': total_failed
                },
                'progress': 100
            })
            yield f"data: {result_data}\n\n"

        except Exception as e:
            error_data = json.dumps({
                'success': False,
                'message': str(e),
                'progress': 0,
                'task_id': task_id
            })
            yield f"data: {error_data}\n\n"
        finally:
            tasks.CANCEL_EVENTS.pop(task_id, None)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


@router.post("/api/upload/cancel/{task_id}")
async def cancel_upload(task_id: str, current_user: User = Depends(require_admin)):
    """取消上传任务"""
    from app import tasks
    if task_id in tasks.CANCEL_EVENTS:
        tasks.CANCEL_EVENTS[task_id].set()
        return {"success": True, "message": "取消信号已发送", "task_id": task_id}
    return {"success": False, "message": "任务不存在或已结束"}

