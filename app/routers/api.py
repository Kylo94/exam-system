"""
REST API 路由
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

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


# ===== 科目 API =====
@router.get("/subjects")
async def list_subjects():
    """获取科目列表"""
    subjects = await Subject.all()
    return {"success": True, "data": subjects}


@router.post("/subjects")
async def create_subject_api(
    name: str,
    description: str = None,
    current_user: User = Depends(require_admin)
):
    """创建科目"""
    subject = await Subject.create(name=name, description=description)
    return {"success": True, "data": {"id": subject.id, "name": subject.name}}


@router.delete("/subjects/{subject_id}")
async def delete_subject_api(subject_id: int, current_user: User = Depends(require_admin)):
    """删除科目"""
    subject = await Subject.get_or_none(id=subject_id)
    if not subject:
        raise HTTPException(status_code=404, detail="科目不存在")
    await subject.delete()
    return {"success": True}


# ===== 难度等级 API =====
@router.get("/levels")
async def list_levels():
    """获取难度等级列表"""
    levels = await Level.all()
    return {"success": True, "data": levels}


@router.post("/levels")
async def create_level_api(
    name: str,
    description: str = None,
    current_user: User = Depends(require_admin)
):
    """创建难度等级"""
    level = await Level.create(name=name, description=description)
    return {"success": True, "data": {"id": level.id, "name": level.name}}


# ===== 知识点 API =====
@router.get("/knowledge-points")
async def list_knowledge_points(subject_id: Optional[int] = None):
    """获取知识点列表"""
    if subject_id:
        kps = await KnowledgePoint.filter(subject_id=subject_id)
    else:
        kps = await KnowledgePoint.all()
    return {"success": True, "data": kps}


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
    max_attempts: int = 1,
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
        max_attempts=max_attempts,
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
    max_attempts: int = None,
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
    if max_attempts:
        exam.max_attempts = max_attempts
    if pass_score:
        exam.pass_score = pass_score
    
    await exam.save()
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
