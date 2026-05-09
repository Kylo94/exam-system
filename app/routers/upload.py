"""上传解析路由"""
import json
import logging
import os
import tempfile
import uuid
from pathlib import Path
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, StreamingResponse

from app.auth import require_admin
from app.models.audit_log import AuditLog
from app.models.exam import Exam
from app.models.knowledge_point import KnowledgePoint
from app.models.user import User
from app.services.exam_service import ExamService
from app.services.knowledge_point_service import KnowledgePointService
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


@router.get("/api/uploads/{filename:path}")
async def serve_upload(filename: str):
    """服务上传的图片文件"""
    file_path = Path("uploads") / filename

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="文件不存在")

    return FileResponse(file_path)


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

    # 获取已有知识点列表（用于AI匹配）
    existing_kps = []
    existing_kp_names = []
    if level_id_int and subject_id_int:
        existing_kps = await KnowledgePoint.filter(
            subject_id=subject_id_int, level_id=level_id_int
        ).all()
        existing_kp_names = [kp.name for kp in existing_kps]

    # 解析文档
    suffix = Path(filename).suffix.lower()
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(file_content)
            tmp_path = tmp.name

        raw_text, questions_data, image_info = await ParsingService.parse_document(
            tmp_path, filename, parse_method, ai_config_obj, existing_kps=existing_kp_names
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
        questions=questions_data,
        existing_kps=existing_kps
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
        def progress_msg(progress, message, level="info", current=0, total=0, details=None):
            data = {
                "progress": progress,
                "message": message,
                "level": level,
                "task_id": task_id,
                "current": current,
                "total": total,
            }
            if details:
                data["details"] = details
            return f"data: {json.dumps(data)}\n\n"

        tmp_path = None
        exam_id = None
        try:
            suffix = Path(filename).suffix.lower()
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                tmp.write(file_content)
                tmp_path = tmp.name

            yield progress_msg(0, f"文件上传完成: {filename}")

            # 获取已有知识点列表（用于AI匹配）
            existing_kp_names = []
            if level_id_int and subject_id_int:
                existing_kps = await KnowledgePoint.filter(
                    subject_id=subject_id_int, level_id=level_id_int
                ).all()
                existing_kp_names = [kp.name for kp in existing_kps]

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
                tmp_path, filename, parse_method, ai_config_obj, existing_kps=existing_kp_names
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

            # 知识点匹配（AI已在batch_enhance_questions中完成知识点分配）
            kp_name_to_obj = {}
            kp_created_count = 0
            knowledge_point_map = {}
            if level_id_int and subject_id_int:
                yield progress_msg(40, "正在处理知识点...")
                try:
                    # 调试：检查questions_data中的知识点字段
                    for idx, q in enumerate(questions_data):
                        kp_names = q.get('knowledge_point_names')
                        logger.debug(f"题{idx+1} knowledge_point_names: {kp_names}")
                        if kp_names:
                            kp_ids = []
                            for kp_name in kp_names:
                                if kp_name not in kp_name_to_obj:
                                    kp = await KnowledgePointService.get_or_create_knowledge_point(
                                        subject_id=subject_id_int,
                                        level_id=level_id_int,
                                        name=kp_name,
                                        description="自动创建"
                                    )
                                    kp_name_to_obj[kp_name] = kp
                                    kp_created_count += 1
                                kp_ids.append(kp_name_to_obj[kp_name].id)
                            knowledge_point_map[idx + 1] = kp_ids
                except Exception as e:
                    logger.warning(f"知识点处理失败: {e}")

            yield progress_msg(55, f"知识点处理完成 (新建{kp_created_count}个)", "success")

            # 创建题目
            yield progress_msg(60, "正在创建题目...")
            created, failed = await ExamService.create_questions_from_data(
                exam, questions_data, knowledge_point_map
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

            UploadService.complete_task(task_id, {"exam_id": exam.id, "created": created, "failed": failed, "kp_created": kp_created_count})
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

    # 知识点匹配（AI已在preview阶段完成知识点分配）
    kp_name_to_obj = {}
    kp_created_count = 0
    knowledge_point_map = {}

    if level_id:
        try:
            for idx, q in enumerate(questions):
                kp_names = q.get('knowledge_point_names', [])
                if kp_names:
                    kp_ids = []
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
                        kp_ids.append(kp_name_to_obj[kp_name].id)
                    knowledge_point_map[idx + 1] = kp_ids
        except Exception as e:
            logger.warning(f"知识点处理失败: {e}")

    # 创建题目
    created, failed = await ExamService.create_questions_from_data(exam, questions, knowledge_point_map)

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
            "questions": {"created": created, "failed": failed, "total": len(questions)},
            "knowledge_points_created": kp_created_count
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
        def progress_msg(progress, message, level="info", current=0, total=0):
            data = {
                "progress": progress,
                "message": message,
                "level": level,
                "task_id": task_id,
                "current": current,
                "total": total
            }
            return f"data: {json.dumps(data)}\n\n"

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

                # 获取已有知识点列表（用于AI匹配）
                existing_kp_names = []
                if level_id_int and subject_id_int:
                    existing_kps = await KnowledgePoint.filter(
                        subject_id=subject_id_int, level_id=level_id_int
                    ).all()
                    existing_kp_names = [kp.name for kp in existing_kps]

                # 解析文件
                suffix = Path(file_name).suffix.lower()
                tmp_path = None
                try:
                    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                        tmp.write(file_content)
                        tmp_path = tmp.name

                    raw_text, questions_data, image_info = await ParsingService.parse_document(
                        tmp_path, file_name, parse_method, ai_config_obj, existing_kps=existing_kp_names
                    )

                    if questions_data:
                        # 从AI结果中提取知识点映射
                        knowledge_point_map = {}
                        kp_name_to_obj = {}
                        for q_idx, q in enumerate(questions_data):
                            kp_names = q.get('knowledge_point_names', [])
                            if kp_names:
                                kp_ids = []
                                for kp_name in kp_names:
                                    if kp_name not in kp_name_to_obj:
                                        kp = await KnowledgePointService.get_or_create_knowledge_point(
                                            subject_id=subject_id_int,
                                            level_id=level_id_int,
                                            name=kp_name,
                                            description="自动创建"
                                        )
                                        kp_name_to_obj[kp_name] = kp
                                    kp_ids.append(kp_name_to_obj[kp_name].id)
                                knowledge_point_map[q_idx + 1] = kp_ids

                        created, failed = await ExamService.create_questions_from_data(exam, questions_data, knowledge_point_map)
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