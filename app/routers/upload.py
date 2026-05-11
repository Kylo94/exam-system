"""上传解析路由"""
import json
import logging
import tempfile
import uuid
from functools import partial
from pathlib import Path
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, StreamingResponse

from app.auth import require_admin
from app.models.audit_log import AuditLog
from app.models.exam import Exam
from app.models.user import User
from app.parsers.constants import sse_progress_msg
from app.services.exam_service import ExamService
from app.services.parsing_service import ParsingService
from app.services.upload_service import UploadService

router = APIRouter()
logger = logging.getLogger(__name__)


# ===== 图片上传 =====

@router.post("/api/upload-image")
async def upload_image(
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


# ===== 文件解析 =====

@router.post("/api/upload/parse")
async def parse_file_preview(
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

    # 解析文档
    suffix = Path(filename).suffix.lower()
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(file_content)
            tmp_path = tmp.name

        raw_text, questions_data, image_info = await ParsingService.parse_document(
            tmp_path, filename, parse_method, ai_config_obj
        )
    except Exception as e:
        return {"success": False, "message": f"文本提取失败: {str(e)}"}
    finally:
        if tmp_path and Path(tmp_path).exists():
            Path(tmp_path).unlink()

    if not questions_data:
        return {"success": False, "message": "未发现任何题目"}

    # 构建预览数据
    preview_data = ParsingService.build_preview_data(
        title=title,
        subject_id=subject_id_int,
        level_id=level_id_int,
        questions=questions_data
    )

    return {"success": True, "data": preview_data}


# ===== 一站式解析+创建（SSE进度）=====

@router.post("/api/exams/from-parsed")
async def create_exam_from_parsed(
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
    """解析文件并创建试卷（SSE实时进度）"""
    task_id = UploadService.create_task()
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
        if not ai_config_obj:
            UploadService.update_progress(task_id, 8, "未找到AI配置，改为本地解析", "warning")
            use_ai_parsing = False

    async def event_stream():
        progress_msg = partial(sse_progress_msg, task_id=task_id)

        tmp_path = None
        exam_id = None
        try:
            suffix = Path(filename).suffix.lower()
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                tmp.write(file_content)
                tmp_path = tmp.name

            yield progress_msg(0, f"文件上传完成: {filename}")

            # 创建试卷
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
            yield progress_msg(5, f"试卷创建成功 (ID: {exam.id})", "success")

            # 解析文档
            yield progress_msg(5, "正在提取文档文本和图片...")
            raw_text, questions_data, image_info = await ParsingService.parse_document(
                tmp_path, filename, parse_method, ai_config_obj
            )
            yield progress_msg(15, f"文本提取完成 ({len(raw_text)}字符, {len(image_info)}张图片)", "success", len(questions_data), len(questions_data))

            if not questions_data:
                yield progress_msg(100, "未发现任何题目", "error")
                return

            # AI增强（如需要）
            if use_ai_parsing:
                q_count = len(questions_data)
                # 根据题目数量估算AI处理时间：约5-10秒/题
                estimated_time = min(q_count * 10, 600)
                minutes = estimated_time // 60
                seconds = estimated_time % 60
                time_str = f"{minutes}分{seconds}秒" if minutes > 0 else f"{seconds}秒"
                yield progress_msg(20, f"正在进行AI增强，预计需要 {time_str} (共{q_count}道题)", "info", 0, q_count)
                yield progress_msg(25, f"AI增强处理中... (如长时间无更新请耐心等待)", "info", 0, q_count)

            # 创建题目（只保存tags，不关联知识点）
            yield progress_msg(60, "正在创建题目...")
            created, failed = await ExamService.create_questions_from_data(
                exam, questions_data
            )
            yield progress_msg(95, f"题目创建完成 (成功{created}道, 失败{failed}道)", "success", created, created)

            # 审计日志
            client_ip = request.client.host if request.client else None
            await AuditLog.log_create(
                user=current_user,
                resource_type="exam",
                resource_id=exam.id,
                description=f"上传文件创建试卷: {title}",
                ip_address=client_ip,
                status="success"
            )

            UploadService.complete_task(task_id, {"exam_id": exam.id, "created": created, "failed": failed})
            yield progress_msg(100, "完成", "success", created, created, {"exam_id": exam.id, "created": created, "failed": failed})

        except Exception as e:
            logger.error(f"创建试卷失败: {e}")
            import traceback
            traceback.print_exc()
            # 清理已创建的试卷
            if exam_id:
                await Exam.filter(id=exam_id).delete()
            UploadService.complete_task(task_id)
            yield progress_msg(100, f"创建失败: {str(e)[:100]}", "error")
        finally:
            if tmp_path and Path(tmp_path).exists():
                Path(tmp_path).unlink()

    return StreamingResponse(event_stream(), media_type="text/event-stream")


# ===== 从JSON创建试卷+题目 =====

@router.post("/api/exams/from-json")
async def create_exam_from_json(
    request: Request,
    current_user: User = Depends(require_admin)
):
    """从JSON创建试卷+题目（保存预览数据）"""
    client_ip = request.client.host if request.client else None

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

    if not questions:
        return {"success": False, "message": "没有题目可保存"}

    if not subject_id:
        return {"success": False, "message": "缺少科目信息"}

    try:
        # 创建试卷
        exam = await ExamService.create_exam(
            title=exam_title,
            subject_id=subject_id,
            level_id=level_id,
            creator=current_user,
            duration_minutes=60,
            total_points=100,
            pass_score=60,
            is_published=False,
        )
    except Exception as e:
        return {"success": False, "message": f"创建试卷失败: {str(e)}"}

    # 创建题目（只保存tags，不关联知识点）
    created, failed = await ExamService.create_questions_from_data(exam, questions)

    # 审计日志
    await AuditLog.log_create(
        user=current_user,
        resource_type="exam",
        resource_id=exam.id,
        description=f"从JSON创建试卷: {exam_title}",
        ip_address=client_ip,
        status="success"
    )

    return {
        "success": True,
        "data": {
            "exam_id": exam.id,
            "questions": {"created": created, "failed": failed, "total": len(questions)}
        }
    }


# ===== 批量上传 =====

@router.post("/api/uploads/batch")
async def batch_upload(
    request: Request,
    current_user: User = Depends(require_admin)
):
    """批量上传并解析文件（SSE实时进度）"""
    import base64

    task_id = UploadService.create_task()
    body = await request.json()

    files_meta = body.get('files', [])
    files_data = body.get('file_data', [])
    parse_method = body.get('parse_method', 'local')
    ai_config_id = body.get('ai_config_id')
    is_published = body.get('is_published', False)

    ai_config_obj = None
    if parse_method == 'ai' and ai_config_id:
        from app.models.ai_config import AIConfig
        ai_config_obj = await AIConfig.get_or_none(id=ai_config_id)

    async def event_stream():
        progress_msg = partial(sse_progress_msg, task_id=task_id)

        total_files = len(files_meta)
        results = []

        try:
            yield progress_msg(0, f"开始批量上传 {total_files} 个文件", "info", 0, total_files)

            for idx, file_meta in enumerate(files_meta):
                if UploadService.is_cancelled(task_id):
                    yield progress_msg(100, "用户取消上传", "warning")
                    return

                file_name = file_meta.get('name', f'file_{idx}')
                file_content_b64 = file_meta.get('content', '')

                try:
                    file_content = base64.b64decode(file_content_b64) if file_content_b64 else b''
                except Exception:
                    file_content = b''

                # 提取标题和科目信息
                title = file_meta.get('title', file_name.replace('.docx', '').replace('.pdf', ''))
                subject_id = file_meta.get('subject_id')
                level_id = file_meta.get('level_id')

                try:
                    subject_id_int = int(subject_id) if subject_id else None
                    level_id_int = int(level_id) if level_id else None
                except (ValueError, TypeError):
                    subject_id_int = None
                    level_id_int = None

                yield progress_msg(
                    int((idx / total_files) * 100),
                    f"解析文件 {idx + 1}/{total_files}: {file_name}",
                    "info", idx + 1, total_files
                )

                # 创建试卷
                exam = await Exam.create(
                    title=title,
                    subject_id=subject_id_int,
                    level_id=level_id_int,
                    creator=current_user,
                    duration_minutes=60,
                    total_points=100,
                    pass_score=60,
                    is_published=is_published,
                )

                # 解析文件
                suffix = Path(file_name).suffix.lower()
                tmp_path = None
                try:
                    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                        tmp.write(file_content)
                        tmp_path = tmp.name

                    raw_text, questions_data, image_info = await ParsingService.parse_document(
                        tmp_path, file_name, parse_method, ai_config_obj
                    )

                    if questions_data:
                        # 创建题目（只保存tags，不关联知识点）
                        created, failed = await ExamService.create_questions_from_data(exam, questions_data)
                        results.append({
                            "file": file_name,
                            "exam_id": exam.id,
                            "success": True,
                            "created": created,
                            "failed": failed
                        })
                        yield progress_msg(
                            int(((idx + 1) / total_files) * 100),
                            f"完成 {file_name}: 成功{created}道题",
                            "success", idx + 1, total_files
                        )
                    else:
                        await exam.delete()
                        results.append({
                            "file": file_name,
                            "success": False,
                            "error": "未发现题目"
                        })
                except Exception as e:
                    await exam.delete()
                    results.append({
                        "file": file_name,
                        "success": False,
                        "error": str(e)
                    })
                finally:
                    if tmp_path and Path(tmp_path).exists():
                        Path(tmp_path).unlink()

            UploadService.complete_task(task_id, {"results": results})
            yield progress_msg(100, f"批量上传完成: {len([r for r in results if r.get('success')])}/{total_files} 成功", "success", total_files, total_files, {"results": results})

        except Exception as e:
            logger.error(f"批量上传失败: {e}")
            UploadService.complete_task(task_id)
            yield progress_msg(100, f"批量上传失败: {str(e)[:100]}", "error")

    return StreamingResponse(event_stream(), media_type="text/event-stream")


# ===== 取消上传 =====

@router.post("/api/uploads/cancel/{task_id}")
async def cancel_upload(task_id: str, current_user: User = Depends(require_admin)):
    """取消上传任务"""
    success = UploadService.cancel_task(task_id)
    return {"success": success, "task_id": task_id}


# ===== 进度查询 =====

@router.get("/api/uploads/progress/{task_id}")
async def get_upload_progress(task_id: str):
    """获取上传任务进度"""
    status = UploadService.get_task_status(task_id)
    if not status:
        return {"success": False, "message": "任务不存在"}
    return {"success": True, "data": status}