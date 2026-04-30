"""管理员 - 题目管理"""
import json
import logging
from pathlib import Path
import uuid
import tempfile
import os

from fastapi import APIRouter, Depends, Request, HTTPException, Form, File, UploadFile, Body
from fastapi.responses import HTMLResponse, StreamingResponse, FileResponse

from app.auth import require_admin
from app.models.user import User
from app.models.exam import Exam
from app.models.subject import Subject
from app.models.level import Level
from app.models.question import Question
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
            "image_data": q.image_data,
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
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/api/questions/{question_id}")
async def admin_delete_question(question_id: int, current_user: User = Depends(require_admin)):
    """删除题目"""
    try:
        await QuestionService.delete_question(question_id)
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/api/questions")
async def admin_list_all_questions(
    exam_id: int = None,
    subject_id: int = None,
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

    total = await query.count()
    questions = await query.prefetch_related("exam", "knowledge_point").order_by("-id").offset((page - 1) * page_size).limit(page_size)

    result = []
    for q in questions:
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
            "knowledge_point": q.knowledge_point.name if q.knowledge_point else None,
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
    question_ids: list[int],
    current_user: User = Depends(require_admin)
):
    """批量删除题目"""
    deleted = await QuestionService.batch_delete(question_ids)
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


@router.get("/api/uploads/{filename:path}")
async def serve_upload(filename: str):
    """服务上传的图片文件"""
    file_path = Path("uploads") / filename

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="文件不存在")

    return FileResponse(file_path)


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

    from app import tasks
    from asyncio import Event
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
            yield progress_msg(5, f'📝 正在提取文档文本和图片...', level='info')
            from app.parsers.docx_extractor import DocxExtractor
            extractor = DocxExtractor(upload_folder='uploads/images')
            try:
                raw_text, image_info = extractor.extract_text_and_images(tmp_path)
                yield progress_msg(10, f'✅ 文本提取完成 ({len(raw_text)}字符, {len(image_info)}张图片)', level='success')
            except Exception as e:
                yield progress_msg(100, f'❌ 文本提取失败: {str(e)[:50]}', level='error')
                return

            # 步骤2: 本地规则拆分题目
            yield progress_msg(15, f'🔍 正在用规则拆分题目...', level='info')
            from app.parsers.rule_parser import RuleParser
            rule_parser = RuleParser()
            local_questions = rule_parser.parse(raw_text, image_info)
            yield progress_msg(20, f'📋 规则拆分完成，发现 {len(local_questions)} 道题目', level='success', current=0, total=len(local_questions))

            if not local_questions:
                yield progress_msg(100, f'❌ 未发现任何题目', level='error')
                return

            questions_data = local_questions

            if not questions_data:
                yield progress_msg(100, f'❌ 未发现任何题目，解析失败', level='error', current=0, total=0)
                return

            # 步骤3: 批量AI处理
            total = len(questions_data)
            ai_results = questions_data

            if not use_ai_parsing or not ai_config_obj:
                yield progress_msg(25, f'📝 跳过AI处理，直接保存题目到数据库', level='info')
            else:
                yield progress_msg(25, f'🤖 开始批量AI处理 ({total}道题目，一次性处理)', level='info', current=0, total=total)

                from app.parsers.ai_parser import AIParser
                try:
                    ai_parser = AIParser(ai_config=ai_config_obj)
                    yield progress_msg(30, f'🤖 AI处理中...', level='info')

                    enhanced_questions = ai_parser.batch_enhance_questions(questions_data, image_info)

                    ai_results = enhanced_questions
                    yield progress_msg(95, f'✅ AI批量处理完成，{len(enhanced_questions)}道题目已增强', level='success', current=total, total=total)

                except Exception as e:
                    yield progress_msg(50, f'⚠️ AI处理失败: {str(e)[:50]}，使用本地解析结果', level='warning')
                    ai_results = questions_data

            # 步骤4: 逐题创建到数据库
            if cancel_event.is_set():
                yield progress_msg(95, f'⚠️ 用户取消，删除已创建的试卷...', level='warning')
                if exam_id:
                    try:
                        exam = await Exam.get_or_none(id=exam_id)
                        if exam:
                            await exam.delete()
                            yield progress_msg(100, f'🗑️ 试卷已删除', level='info')
                    except Exception as del_exam_error:
                        yield progress_msg(100, f'⚠️ 删除试卷失败: {str(del_exam_error)}', level='error')
                return

            yield progress_msg(95, f'💾 开始保存题目到数据库...', level='info')

            created_count = 0
            failed_count = 0

            for idx, q_data in enumerate(questions_data):
                if cancel_event.is_set():
                    yield progress_msg(95, f'⚠️ 用户取消，停止保存...', level='warning')
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

                    await Question.create(
                        exam=exam,
                        type=final_data.get('type', 'choice') or 'choice',
                        content=final_data.get('content') or '题目内容',
                        options=final_data.get('options') or {},
                        correct_answer=final_data.get('correct_answer') or '',
                        points=final_data.get('points') or 10,
                        difficulty=final_data.get('difficulty') or 1,
                        images=images,
                        question_metadata=final_data.get('question_metadata', {}),
                        order_num=idx + 1,
                    )
                    created_count += 1

                    yield progress_msg(
                        95 + int((idx + 1) / total * 5),
                        f'✅ 第{idx+1}题已保存',
                        level='success',
                        current=idx + 1,
                        total=total,
                        details=[f'[{idx+1}/{total}] ✅ {q_type_display}: {q_content_preview} - 已保存']
                    )

                except Exception as q_error:
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
                yield progress_msg(100, f'❌ 创建失败，未成功创建任何题目', 'error', current=0, total=total)

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


@router.post("/api/upload/cancel/{task_id}")
async def cancel_upload(task_id: str, current_user: User = Depends(require_admin)):
    """取消上传任务"""
    from app import tasks
    if task_id in tasks.CANCEL_EVENTS:
        tasks.CANCEL_EVENTS[task_id].set()
        return {"success": True, "message": "取消信号已发送", "task_id": task_id}
    return {"success": False, "message": "任务不存在或已结束"}