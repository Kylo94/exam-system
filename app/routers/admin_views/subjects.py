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
from app.parsers.constants import sse_progress_msg
from app.services.subject_service import SubjectService
from app.services.knowledge_point_service import KnowledgePointService
from app.templating import templates

router = APIRouter()
logger = logging.getLogger(__name__)

# 垃圾标签黑名单：运算符、关键字、文件后缀、太泛的单词
_GARBAGE_TAGS = {
    '+', '-', '*', '/', '//', '%', '**', '+=', '-=', '*=', '/=', '%=', '**=',
    '==', '!=', '>', '<', '>=', '<=', '=', ':=', '->',
    '.py', '.pyc', '.pyw', 'py', 'pyc',
    'True', 'False', 'None', 'and', 'or', 'not', 'is', 'in', 'if', 'else',
    'elif', 'for', 'while', 'break', 'continue', 'return', 'yield', 'pass',
    'def', 'class', 'lambda', 'try', 'except', 'finally', 'raise', 'assert',
    'import', 'from', 'as', 'with', 'del', 'global', 'nonlocal',
    '变量', '字符串', '整数', '浮点数', '列表', '字典', '元组', '集合',
    '函数', '类', '对象', '模块', '文件',
}

_GARBAGE_PATTERNS = [
    r'^[A-Z]$',                                                               # 单字母
    r'^\d+$',                                                                 # 纯数字
    r'^(print|input|int|str|float|list|dict|set|tuple|bool|type|len|range'
    r'|sorted|reversed|enumerate|zip|map|filter|abs|min|max|sum|round'
    r'|open|id|dir|help|exit|quit)$',                                         # 内置函数名
    r'^[A-Z][a-z]+Error$',                                                    # 错误类型
]


def _is_garbage_tag(tag: str) -> bool:
    import re
    if tag in _GARBAGE_TAGS:
        return True
    for pattern in _GARBAGE_PATTERNS:
        if re.match(pattern, tag):
            return True
    return False


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
        progress_msg = sse_progress_msg

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


# ===== AI根据标签生成知识点 =====
@router.post("/api/knowledge-points/generate-from-tags")
async def generate_knowledge_points_from_tags(
    request: Request,
    subject_id: int,
    level_id: int,
    current_user: User = Depends(require_admin)
):
    """AI根据标签生成知识点（SSE实时进度）"""

    async def event_stream():
        progress_msg = sse_progress_msg

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

            # 获取该科目等级下所有题目的标签
            from app.models.question import Question
            from app.models.knowledge_point import KnowledgePoint

            all_tags_list = await Question.filter(
                exam__subject_id=subject_id, exam__level_id=level_id
            ).values_list('tags', flat=True)
            all_tags_set = set()
            garbage_count = 0
            for tags in all_tags_list:
                for tag in (tags or []):
                    t = tag.strip()
                    if not t:
                        continue
                    if _is_garbage_tag(t):
                        garbage_count += 1
                    else:
                        all_tags_set.add(t)

            if garbage_count > 0:
                logger.info(f"过滤垃圾标签: {garbage_count} 个")

            if not all_tags_set:
                yield progress_msg(100, "该等级下暂无题目标签", "warning")
                return

            all_tags = sorted(list(all_tags_set))
            existing_kps = await KnowledgePoint.filter(
                subject_id=subject_id, level_id=level_id
            ).only('name', 'tags').all()
            existing_kp_tags = set()
            for kp in existing_kps:
                for tag in (kp.tags or []):
                    if tag.strip():
                        existing_kp_tags.add(tag.strip())

            uncovered_tags = all_tags_set - existing_kp_tags
            yield progress_msg(10, f"发现 {len(all_tags)} 个标签，其中 {len(uncovered_tags)} 个未归类", "info")

            if not uncovered_tags:
                yield progress_msg(100, "所有标签都已归类，无需生成", "success")
                return

            # 构建给AI的prompt
            tags_str = ", ".join(sorted(uncovered_tags))
            existing_kp_str = "\n".join([f"- {kp.name} (标签: {', '.join(kp.tags or [])})" for kp in existing_kps]) if existing_kps else "（暂无已有知识点）"

            # 获取科目名称
            subject = await Subject.get_or_none(id=subject_id)
            subject_name = subject.name if subject else "未知科目"

            prompt = f"""你需要为「{subject_name}」科目的试题标签创建知识点定义。

已有知识点：
{existing_kp_str}

待归类标签（共 {len(uncovered_tags)} 个）：
{tags_str}

请将标签分组为知识点。要求：
1. 知识点必须与「{subject_name}」科目相关，不要创建无关的知识点
2. 每个知识点的标签应当含义相近或属于同一范畴
3. 标签本身如果太过宽泛（如只含科目名、无具体含义的），可以忽略不创建知识点

返回JSON数组格式：
[{{"name":"知识点名称","tags":["标签1","标签2"],"description":"简要描述"}},...]

注意：
1. 知识点名称要简洁准确，体现「{subject_name}」科目的特点
2. 每个标签只能属于一个知识点
3. 不要为宽泛、无关的标签强制创建知识点
4. 返回JSON数组，不要任何其他文字，不要用markdown包裹
"""

            messages = [
                {'role': 'system', 'content': '你是一个专业的知识点分类助手，擅长将标签归类为知识点。'},
                {'role': 'user', 'content': prompt}
            ]

            logger.info(f"===== AI 生成知识点请求开始 =====")
            logger.info(f"待归类标签: {sorted(uncovered_tags)}")
            logger.info(f"System: {messages[0]['content']}")
            logger.info(f"User prompt:\n{prompt}")
            logger.info(f"===== 发送给AI =====")

            response = llm_service.provider_instance.chat_completion(messages)
            logger.info(f"===== AI 生成知识点响应 ({len(response)} 字符) =====")
            logger.info(f"响应内容:\n{response[:2000]}")

            # 解析AI响应
            import re
            try:
                suggestions = json.loads(response.strip())
            except json.JSONDecodeError:
                json_match = re.search(r'```json\s*(\[[\s\S]*?\])\s*```', response)
                if json_match:
                    try:
                        suggestions = json.loads(json_match.group(1).strip())
                    except json.JSONDecodeError:
                        suggestions = []
                else:
                    suggestions = []

            if not suggestions:
                yield progress_msg(100, "AI未返回有效结果", "error")
                return

            yield progress_msg(40, f"AI建议了 {len(suggestions)} 个知识点，正在创建...", "info")

            # 创建知识点
            created = 0
            for sg in suggestions:
                name = sg.get('name', '').strip()
                tags_list = sg.get('tags', [])
                description = sg.get('description', '自动生成')

                if not name or not tags_list:
                    continue

                # 过滤掉已被现有知识点覆盖的标签
                new_tags = [t for t in tags_list if t in uncovered_tags]
                if not new_tags:
                    continue

                kp = await KnowledgePointService.get_or_create_knowledge_point(
                    subject_id=subject_id,
                    level_id=level_id,
                    name=name,
                    description=description,
                    tags=new_tags
                )
                created += 1
                logger.info(f"创建知识点: {name}, tags: {new_tags}")

            yield progress_msg(100, f"完成，已创建 {created} 个知识点", "success", details={"created": created})

        except Exception as e:
            logger.exception(f"AI生成知识点失败: {e}")
            yield progress_msg(100, f"生成失败: {str(e)}", "error")

    return StreamingResponse(event_stream(), media_type="text/event-stream")
