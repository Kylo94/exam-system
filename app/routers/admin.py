"""
管理员路由
"""
from fastapi import APIRouter, Depends, Request, HTTPException, Form, File, UploadFile, Body
from typing import Optional
from fastapi.responses import HTMLResponse, StreamingResponse, FileResponse
from tortoise.queryset import Q

from app.auth import get_current_user, require_admin
from app.models.user import User
from app.models.exam import Exam
from app.models.subject import Subject
from app.models.level import Level
from app.models.knowledge_point import KnowledgePoint
from app.models.submission import Submission
from app.models.teacher_bind_request import TeacherBindRequest
from app.models.question import Question
from app.templating import templates

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def admin_home(request: Request, current_user: User = Depends(require_admin)):
    """管理员首页"""
    total_users = await User.all().count()
    total_exams = await Exam.all().count()
    total_subjects = await Subject.all().count()
    total_levels = await Level.all().count()

    return templates.TemplateResponse("admin/index.html", {
        "request": request,
        "current_user": current_user,
        "stats": {
            "total_users": total_users,
            "total_exams": total_exams,
            "total_subjects": total_subjects,
            "total_levels": total_levels,
        }
    })


# ===== 用户管理 =====
@router.get("/users", response_class=HTMLResponse)
async def admin_users(
    request: Request,
    page: int = 1,
    page_size: int = 20,
    role: str = None,
    search: str = None,
    current_user: User = Depends(require_admin)
):
    """用户列表"""
    query = User.all()

    # 筛选
    if role:
        query = query.filter(role=role)
    if search:
        query = query.filter(Q(username__contains=search) | Q(email__contains=search))

    # 总数
    total = await query.count()

    # 分页
    offset = (page - 1) * page_size
    users = await query.order_by("-created_at").offset(offset).limit(page_size)

    total_pages = (total + page_size - 1) // page_size if total > 0 else 1

    return templates.TemplateResponse("admin/users.html", {
        "request": request,
        "current_user": current_user,
        "users": users,
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": total_pages
        },
        "filters": {"role": role, "search": search}
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


@router.post("/users/create")
async def create_user(request: Request, username: str = Form(...), email: str = Form(...), password: str = Form(...), role: str = Form("student")):
    """创建用户"""
    from app.auth import get_password_hash

    if await User.get_or_none(username=username):
        raise HTTPException(status_code=400, detail="用户名已存在")

    if await User.get_or_none(email=email):
        raise HTTPException(status_code=400, detail="邮箱已被注册")

    if role not in ["admin", "teacher", "student"]:
        raise HTTPException(status_code=400, detail="无效的角色")

    user = User(
        username=username,
        email=email,
        password_hash=get_password_hash(password),
        role=role
    )
    await user.save()

    return {"success": True, "id": user.id}


# ===== 科目管理 =====
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
    subject = await Subject.create(name=name, description=description)

    # 自动创建等级
    for i in range(1, level_count + 1):
        level_name = f"第{i}级"
        await Level.create(name=level_name, description=f"{level_name}难度", subject=subject)

    return {"success": True, "id": subject.id}


@router.post("/subjects/{subject_id}/levels")
async def create_level_for_subject(
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
    return {"success": True, "id": level.id}


@router.get("/subjects/{subject_id}")
async def get_subject(subject_id: int, current_user: User = Depends(require_admin)):
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


@router.put("/subjects/{subject_id}")
async def update_subject(
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

    return {"success": True}


@router.put("/levels/{level_id}")
async def update_level(
    level_id: int,
    name: str,
    description: str = None,
    current_user: User = Depends(require_admin)
):
    """更新等级"""
    level = await Level.get_or_none(id=level_id)
    if not level:
        raise HTTPException(status_code=404, detail="等级不存在")

    level.name = name
    level.description = description
    await level.save()

    return {"success": True}


@router.delete("/subjects/{subject_id}")
async def delete_subject(subject_id: int, current_user: User = Depends(require_admin)):
    """删除科目（同时删除关联的等级）"""
    subject = await Subject.get_or_none(id=subject_id)
    if not subject:
        raise HTTPException(status_code=404, detail="科目不存在")

    await subject.delete()
    return {"success": True}


@router.delete("/levels/{level_id}")
async def delete_level(level_id: int, current_user: User = Depends(require_admin)):
    """删除难度等级"""
    level = await Level.get_or_none(id=level_id)
    if not level:
        raise HTTPException(status_code=404, detail="等级不存在")

    await level.delete()
    return {"success": True}


# ===== 独立的等级管理（已废弃，合并到科目管理）=====
@router.get("/levels", response_class=HTMLResponse)
async def admin_levels_redirect(request: Request, current_user: User = Depends(require_admin)):
    """重定向到科目管理"""
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/admin/subjects", status_code=303)


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
async def admin_knowledge_points(
    request: Request,
    page: int = 1,
    page_size: int = 20,
    subject_id: int = None,
    level_id: int = None,
    search: str = None,
    current_user: User = Depends(require_admin)
):
    """知识点列表"""
    query = KnowledgePoint.all()

    if subject_id:
        query = query.filter(subject_id=subject_id)
    if level_id:
        query = query.filter(level_id=level_id)
    if search:
        query = query.filter(Q(name__contains=search) | Q(description__contains=search))

    total = await query.count()
    offset = (page - 1) * page_size
    kps = await query.prefetch_related("subject", "level").order_by("subject__name", "name").offset(offset).limit(page_size)
    subjects = await Subject.all()
    levels = await Level.all()

    total_pages = (total + page_size - 1) // page_size if total > 0 else 1

    return templates.TemplateResponse("admin/knowledge_points.html", {
        "request": request,
        "current_user": current_user,
        "knowledge_points": kps,
        "subjects": subjects,
        "levels": levels,
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": total_pages
        },
        "filters": {"subject_id": subject_id, "level_id": level_id, "search": search}
    })


# ===== 试卷管理 =====
@router.get("/exams", response_class=HTMLResponse)
async def admin_exams(
    request: Request,
    page: int = 1,
    page_size: int = 20,
    subject_id: int = None,
    level_id: int = None,
    status: str = None,
    search: str = None,
    current_user: User = Depends(require_admin)
):
    """试卷列表"""
    query = Exam.all()

    if subject_id:
        query = query.filter(subject_id=subject_id)
    if level_id:
        query = query.filter(level_id=level_id)
    if status == "published":
        query = query.filter(is_published=True)
    elif status == "draft":
        query = query.filter(is_published=False)
    if search:
        query = query.filter(Q(title__contains=search))

    total = await query.count()
    offset = (page - 1) * page_size
    exams = await query.prefetch_related("subject", "level", "creator").order_by("-created_at").offset(offset).limit(page_size)
    subjects = await Subject.all()
    levels = await Level.all()

    total_pages = (total + page_size - 1) // page_size if total > 0 else 1

    return templates.TemplateResponse("admin/exams.html", {
        "request": request,
        "current_user": current_user,
        "exams": exams,
        "subjects": subjects,
        "levels": levels,
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": total_pages
        },
        "filters": {"subject_id": subject_id, "level_id": level_id, "status": status, "search": search}
    })


@router.get("/api/exams/{exam_id}")
async def get_exam_admin(exam_id: int, current_user: User = Depends(require_admin)):
    """获取试卷详情"""
    exam = await Exam.get_or_none(id=exam_id)
    if not exam:
        raise HTTPException(status_code=404, detail="试卷不存在")
    return {
        "success": True,
        "data": {
            "id": exam.id,
            "title": exam.title,
            "subject_id": exam.subject_id,
            "level_id": exam.level_id,
            "duration_minutes": exam.duration_minutes,
            "total_points": exam.total_points,
            "pass_score": exam.pass_score,
            "is_published": exam.is_published,
            "is_active": exam.is_published,
        }
    }


@router.put("/api/exams/{exam_id}")
async def update_exam_admin(
    exam_id: int,
    request: Request,
    current_user: User = Depends(require_admin)
):
    """更新试卷"""
    exam = await Exam.get_or_none(id=exam_id)
    if not exam:
        raise HTTPException(status_code=404, detail="试卷不存在")

    body = await request.json()

    if 'title' in body and body['title']:
        exam.title = body['title']
    if 'subject_id' in body:
        exam.subject_id = body['subject_id']
    if 'level_id' in body:
        exam.level_id = body['level_id']
    if 'duration_minutes' in body:
        exam.duration_minutes = body['duration_minutes']
    if 'total_points' in body:
        exam.total_points = body['total_points']
    if 'pass_score' in body:
        exam.pass_score = body['pass_score']
    if 'is_published' in body:
        exam.is_published = body['is_published']

    await exam.save()
    return {"success": True}


@router.post("/api/exams")
async def create_exam_admin(
    title: str = Form(...),
    subject_id: int = Form(...),
    level_id: int = Form(None),
    duration_minutes: int = Form(60),
    total_points: int = Form(100),
    pass_score: int = Form(60),
    is_published: bool = Form(False),
    current_user: User = Depends(require_admin)
):
    """创建试卷"""
    exam = await Exam.create(
        title=title,
        subject_id=subject_id,
        level_id=level_id,
        creator=current_user,
        duration_minutes=duration_minutes,
        total_points=total_points,
        pass_score=pass_score,
        is_published=is_published,
    )
    return {"success": True, "data": {"id": exam.id}}


@router.get("/exams/{exam_id}/edit", response_class=HTMLResponse)
async def admin_edit_exam_page(exam_id: int, request: Request, current_user: User = Depends(require_admin)):
    """编辑试卷页面"""
    exam = await Exam.get_or_none(id=exam_id)
    if not exam:
        raise HTTPException(status_code=404, detail="试卷不存在")

    subjects = await Subject.all()
    levels = await Level.all()
    questions = await Question.filter(exam_id=exam_id).order_by("order_num")

    return templates.TemplateResponse("exam_edit.html", {
        "request": request,
        "current_user": current_user,
        "subjects": subjects,
        "levels": levels,
        "exam": exam,
        "questions": questions,
        "is_admin": True
    })


# ===== 题目管理 API =====
@router.get("/api/exams/{exam_id}/questions")
async def admin_list_questions(exam_id: int, current_user: User = Depends(require_admin)):
    """获取试卷题目列表"""
    questions = await Question.filter(exam_id=exam_id).order_by("order_num")
    # 转换为字典列表，包含图片信息
    result = []
    for q in questions:
        result.append({
            "id": q.id,
            "exam_id": q.exam_id,
            "type": q.type,
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
        })
    return {"success": True, "data": result}


@router.post("/api/exams/{exam_id}/questions")
async def admin_create_question(
    exam_id: int,
    request: Request,
    current_user: User = Depends(require_admin)
):
    """创建题目"""
    import json

    exam = await Exam.get_or_none(id=exam_id)
    if not exam:
        raise HTTPException(status_code=404, detail="试卷不存在")

    body = await request.json()

    type = body.get('type', 'single_choice')
    content = body.get('content', '')
    correct_answer = body.get('correct_answer', '')
    points = body.get('points', 10)
    options = body.get('options', {})
    explanation = body.get('explanation')
    difficulty = body.get('difficulty', 1)
    has_image = body.get('has_image', False)
    image_data = body.get('image_data')
    question_metadata = body.get('question_metadata', {})

    if isinstance(options, str):
        options = json.loads(options) if options else {}
    if isinstance(question_metadata, str):
        question_metadata = json.loads(question_metadata) if question_metadata else {}

    question = await Question.create(
        exam=exam,
        type=type,
        content=content,
        correct_answer=correct_answer,
        points=points,
        options=options,
        explanation=explanation,
        difficulty=difficulty,
        has_image=has_image,
        image_data=image_data,
        question_metadata=question_metadata,
        order_num=await Question.filter(exam_id=exam_id).count() + 1,
    )
    return {"success": True, "data": {"id": question.id}}


@router.get("/api/questions/{question_id}")
async def admin_get_question(
    question_id: int,
    current_user: User = Depends(require_admin)
):
    """获取题目详情"""
    question = await Question.get_or_none(id=question_id)
    if not question:
        raise HTTPException(status_code=404, detail="题目不存在")
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


@router.put("/api/questions/{question_id}")
async def admin_update_question(
    question_id: int,
    request: Request,
    current_user: User = Depends(require_admin)
):
    """更新题目"""
    import json
    import logging
    logger = logging.getLogger(__name__)

    question = await Question.get_or_none(id=question_id)
    if not question:
        raise HTTPException(status_code=404, detail="题目不存在")

    # 获取JSON body
    body = await request.json()
    logger.info(f"[update_question] Request body: {body}")

    type = body.get('type')
    content = body.get('content')
    correct_answer = body.get('correct_answer')
    points = body.get('points')
    options = body.get('options')
    explanation = body.get('explanation')
    difficulty = body.get('difficulty')
    has_image = body.get('has_image')
    image_data = body.get('image_data')
    question_metadata = body.get('question_metadata')

    logger.info(f"[update_question] Parsed - has_image={has_image}, image_data={image_data}")

    if type:
        question.type = type
    if content:
        question.content = content
    if correct_answer:
        question.correct_answer = correct_answer
    if points:
        question.points = points
    if options:
        if isinstance(options, str):
            options = json.loads(options)
        question.options = options
    if explanation is not None:
        question.explanation = explanation
    if difficulty:
        question.difficulty = difficulty

    # 处理 has_image 和 image_data
    if has_image is not None:
        question.has_image = has_image
        logger.info(f"[update_question] Set has_image = {has_image}")

    if image_data is not None:
        if image_data == '':
            # 清除图片
            question.image_data = None
            question.has_image = False
            logger.info(f"[update_question] Image cleared for question {question_id}")
        else:
            question.image_data = image_data
            logger.info(f"[update_question] Image set to: {image_data}")

    if question_metadata is not None:
        if isinstance(question_metadata, str):
            question_metadata = json.loads(question_metadata)
        question.question_metadata = question_metadata or {}

    await question.save()
    logger.info(f"[update_question] Saved. Final has_image={question.has_image}, image_data={question.image_data}")
    return {"success": True}


@router.delete("/api/questions/{question_id}")
async def admin_delete_question(question_id: int, current_user: User = Depends(require_admin)):
    """删除题目"""
    question = await Question.get_or_none(id=question_id)
    if not question:
        raise HTTPException(status_code=404, detail="题目不存在")

    await question.delete()
    return {"success": True}


@router.post("/api/upload-image")
async def admin_upload_image(
    file: UploadFile = File(...),
    current_user: User = Depends(require_admin)
):
    """上传图片"""
    import os
    import uuid
    from pathlib import Path

    # 允许的文件类型
    allowed_types = {'image/jpeg', 'image/png', 'image/gif', 'image/webp'}
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="不支持的图片格式")

    # 生成唯一文件名
    ext = Path(file.filename).suffix.lower()
    filename = f"{uuid.uuid4().hex}{ext}"
    upload_dir = Path("uploads/images")
    upload_dir.mkdir(parents=True, exist_ok=True)

    file_path = upload_dir / filename

    content = await file.read()
    with open(file_path, 'wb') as f:
        f.write(content)

    # 返回相对路径（去掉 uploads/ 前缀）
    relative_path = f"images/{filename}"
    return {"success": True, "data": {"path": relative_path}}


@router.get("/api/uploads/{filename:path}")
async def serve_upload(filename: str):
    """服务上传的图片文件"""
    from pathlib import Path

    file_path = Path("uploads") / filename

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="文件不存在")

    return FileResponse(file_path)


@router.post("/api/upload/parse")
async def parse_upload_file(
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
    """解析上传的文件并创建试卷"""
    import tempfile
    import os
    from pathlib import Path

    # 转换subject_id和level_id
    try:
        subject_id_int = int(subject_id) if subject_id else None
    except (ValueError, TypeError):
        subject_id_int = None
    try:
        level_id_int = int(level_id) if level_id else None
    except (ValueError, TypeError):
        level_id_int = None

    # 保存上传的文件
    suffix = Path(file.filename).suffix.lower()
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
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

        # 根据解析方式处理
        questions_data = []
        use_ai_parsing = parse_method == "ai" and ai_config_id
        ai_parsing_failed = False

        # 调试日志
        import logging
        import sys
        logger = logging.getLogger(__name__)
        print(f"[Upload Parse] START parse_method={parse_method}, ai_config_id={ai_config_id}, use_ai_parsing={use_ai_parsing}", flush=True)
        logger.info(f"[Upload Parse] parse_method={parse_method}, ai_config_id={ai_config_id}, use_ai_parsing={use_ai_parsing}")

        if use_ai_parsing:
            from app.models.ai_config import AIConfig
            ai_config = await AIConfig.get_or_none(id=ai_config_id)
            print(f"[Upload Parse] ai_config found: {ai_config}", flush=True)
            logger.info(f"[Upload Parse] ai_config found: {ai_config}")
            if ai_config:
                try:
                    from app.parsers.question_parser import QuestionParser
                    parser = QuestionParser(ai_config=ai_config)
                    print(f"[Upload Parse] Starting AI parse with config: {ai_config.provider} - {ai_config.model}", flush=True)
                    logger.info(f"[Upload Parse] Starting AI parse with config: {ai_config.provider} - {ai_config.model}")
                    result = parser.parse_document(tmp_path)
                    questions_data = result.get('questions', [])
                    print(f"[Upload Parse] AI parse result: {len(questions_data)} questions", flush=True)
                    logger.info(f"[Upload Parse] AI parse result: {len(questions_data)} questions")
                    logger.info(f"[Upload Parse] AI parse logs: {result.get('parse_log', 'N/A')[:500]}")
                except Exception as e:
                    import traceback
                    print(f"[Upload Parse] AI parse FAILED: {str(e)}", flush=True)
                    traceback.print_exc(file=sys.stdout)
                    logger.error(f"[Upload Parse] AI parse failed: {str(e)}")
                    logger.error(f"[Upload Parse] Traceback: {traceback.format_exc()}")
                    ai_parsing_failed = True

        # 如果AI解析未启用、失败或返回空，使用本地规则解析
        if not questions_data:
            print(f"[Upload Parse] Falling back to local parsing, use_ai_parsing={use_ai_parsing}, ai_parsing_failed={ai_parsing_failed}", flush=True)
            logger.info(f"[Upload Parse] Falling back to local parsing, use_ai_parsing={use_ai_parsing}, ai_parsing_failed={ai_parsing_failed}")
            from app.parsers.factory import ParserFactory
            try:
                parsed = ParserFactory.parse_file(tmp_path)
                questions_data = parsed.get('questions', [])
                print(f"[Upload Parse] Local parse result: {len(questions_data)} questions", flush=True)
                logger.info(f"[Upload Parse] Local parse result: {len(questions_data)} questions")
            except Exception as e:
                print(f"[Upload Parse] Local parse failed: {str(e)}", flush=True)
                logger.error(f"[Upload Parse] Local parse failed: {str(e)}")

        # 创建题目
        created_count = 0
        for idx, q_data in enumerate(questions_data):
            from app.models.question import Question
            # 确保 correct_answer 不为 None
            correct_answer = q_data.get('correct_answer') or ''
            await Question.create(
                exam=exam,
                type=q_data.get('type', 'choice') or 'choice',
                content=q_data.get('content') or '题目内容',
                options=q_data.get('options') or {},
                correct_answer=correct_answer,
                points=q_data.get('points') or 10,
                difficulty=q_data.get('difficulty') or 1,
                has_image=q_data.get('content_has_image', False),
                image_data=q_data.get('image_path', None),
                question_metadata=q_data.get('question_metadata', {}),
                order_num=idx + 1,
            )
            created_count += 1

        return {
            "success": True,
            "data": {
                "exam_id": exam.id,
                "questions": {"created": created_count}
            }
        }
    except Exception as e:
        return {"success": False, "message": str(e)}
    finally:
        os.unlink(tmp_path)


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
    """解析上传的文件并创建试卷（支持SSE实时进度）"""
    import tempfile
    import os
    import json
    from pathlib import Path

    # 先读取文件内容（必须在StreamingResponse之前）
    file_content = await file.read()
    filename = file.filename

    # 转换subject_id和level_id
    try:
        subject_id_int = int(subject_id) if subject_id else None
    except (ValueError, TypeError):
        subject_id_int = None
    try:
        level_id_int = int(level_id) if level_id else None
    except (ValueError, TypeError):
        level_id_int = None

    async def event_stream():
        """SSE事件流生成器"""

        def progress_msg(progress, message='', level='info'):
            """发送进度消息"""
            data = json.dumps({
                'progress': progress,
                'message': message,
                'level': level
            })
            return f"data: {data}\n\n"

        tmp_path = None
        try:
            # 保存上传的文件到临时文件
            suffix = Path(filename).suffix.lower()
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                tmp.write(file_content)
                tmp_path = tmp.name

            # 发送初始进度
            yield progress_msg(5, '文件上传完成，开始解析...')

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

            yield progress_msg(10, '试卷创建成功，开始解析文档...')

            # 根据解析方式处理
            questions_data = []
            use_ai_parsing = parse_method == "ai" and ai_config_id

            if use_ai_parsing:
                from app.models.ai_config import AIConfig
                ai_config = await AIConfig.get_or_none(id=ai_config_id)
                if ai_config:
                    yield progress_msg(15, f'使用{ai_config.provider} AI解析中，请稍候...')
                    from app.parsers.question_parser import QuestionParser
                    parser = QuestionParser(ai_config=ai_config)
                    result = parser.parse_document(tmp_path)
                    questions_data = result.get('questions', [])
                    yield progress_msg(70, f'AI解析完成，找到{len(questions_data)}道题目')

            # 如果AI解析未启用、失败或返回空，使用本地规则解析
            if not questions_data:
                yield progress_msg(30, '使用本地规则解析中...')
                from app.parsers.factory import ParserFactory
                try:
                    parsed = ParserFactory.parse_file(tmp_path)
                    questions_data = parsed.get('questions', [])
                    yield progress_msg(70, f'本地解析完成，找到{len(questions_data)}道题目')
                except Exception as e:
                    yield progress_msg(70, f'解析完成，{len(questions_data)}道题目')

            # 创建题目
            yield progress_msg(75, f'正在创建{len(questions_data)}道题目...')
            created_count = 0
            for idx, q_data in enumerate(questions_data):
                from app.models.question import Question
                correct_answer = q_data.get('correct_answer') or ''
                await Question.create(
                    exam=exam,
                    type=q_data.get('type', 'choice') or 'choice',
                    content=q_data.get('content') or '题目内容',
                    options=q_data.get('options') or {},
                    correct_answer=correct_answer,
                    points=q_data.get('points') or 10,
                    difficulty=q_data.get('difficulty') or 1,
                    has_image=q_data.get('content_has_image', False),
                    image_data=q_data.get('image_path', None),
                    question_metadata=q_data.get('question_metadata', {}),
                    order_num=idx + 1,
                )
                created_count += 1
                # 每创建5题发送一次进度
                if idx % 5 == 0:
                    pct = 75 + int((idx / len(questions_data)) * 20)
                    yield progress_msg(pct, f'已创建 {idx + 1}/{len(questions_data)} 道题目')

            yield progress_msg(100, f'完成！共创建 {created_count} 道题目', 'success')

            # 返回最终结果
            result_data = json.dumps({
                'success': True,
                'data': {
                    'exam_id': exam.id,
                    'questions': {'created': created_count}
                },
                'progress': 100
            })
            yield f"data: {result_data}\n\n"

        except Exception as e:
            import traceback
            error_data = json.dumps({
                'success': False,
                'message': str(e),
                'progress': 0
            })
            yield f"data: {error_data}\n\n"
        finally:
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


# ===== 绑定申请管理 =====
@router.get("/bind-requests", response_class=HTMLResponse)
async def admin_bind_requests(request: Request, current_user: User = Depends(require_admin)):
    """学生绑定申请列表"""
    requests = await TeacherBindRequest.all().prefetch_related("student", "teacher").order_by("-created_at")
    return templates.TemplateResponse("admin/bind_requests.html", {
        "request": request,
        "current_user": current_user,
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
        "current_user": current_user,
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
        "current_user": current_user,
        "ai_configs": ai_configs,
        "is_admin_view": True
    })
