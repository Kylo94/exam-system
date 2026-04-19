"""
学生路由
"""
from fastapi import APIRouter, Depends, Request, HTTPException, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from datetime import datetime
import random

from app.auth import get_current_user, require_student
from app.models.user import User
from app.models.exam import Exam
from app.models.question import Question
from app.models.submission import Submission
from app.models.answer import Answer
from app.models.subject import Subject
from app.templating import templates

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def student_home(request: Request, current_user: User = Depends(require_student)):
    """学生首页"""
    return templates.TemplateResponse("student/index.html", {
        "request": request,
        "user": current_user
    })


# ===== 专项刷题 =====
@router.get("/practice", response_class=HTMLResponse)
async def student_practice(request: Request, current_user: User = Depends(require_student)):
    """专项刷题页面"""
    subjects = await Subject.all().order_by("name")
    return templates.TemplateResponse("student/practice.html", {
        "request": request,
        "user": current_user,
        "subjects": subjects
    })


@router.get("/practice/{subject_id}", response_class=HTMLResponse)
async def practice_by_subject(subject_id: int, request: Request, current_user: User = Depends(require_student)):
    """按科目刷题"""
    subject = await Subject.get_or_none(id=subject_id)
    if not subject:
        raise HTTPException(status_code=404, detail="科目不存在")

    # 获取该科目的题目
    questions = await Question.filter(subject_id=subject_id).limit(10)
    # 随机打乱
    random.shuffle(questions)

    return templates.TemplateResponse("student/practice_questions.html", {
        "request": request,
        "user": current_user,
        "subject": subject,
        "questions": questions
    })


# ===== 我的试卷 =====
@router.get("/exams", response_class=HTMLResponse)
async def student_exams(request: Request, current_user: User = Depends(require_student)):
    """可参加的试卷列表"""
    exams = await Exam.filter(is_published=True).prefetch_related("subject", "level").order_by("-created_at")
    
    # 获取用户的提交记录
    submissions = await Submission.filter(user_id=current_user.id).values_list("exam_id", flat=True)
    
    return templates.TemplateResponse("student/exams.html", {
        "request": request,
        "user": current_user,
        "exams": exams,
        "completed_exam_ids": list(submissions)
    })


# ===== 答题页面 =====
@router.get("/exam/{exam_id}/take", response_class=HTMLResponse)
async def take_exam(exam_id: int, request: Request, current_user: User = Depends(require_student)):
    """答题页面"""
    exam = await Exam.get_or_none(id=exam_id).prefetch_related("questions")
    
    if not exam:
        raise HTTPException(status_code=404, detail="试卷不存在")
    
    # 获取或创建答题记录
    submission = await Submission.filter(
        exam_id=exam_id,
        user_id=current_user.id,
        status="in_progress"
    ).first()
    
    if not submission:
        # 检查是否已完成
        attempt_count = await Submission.filter(
            exam_id=exam_id,
            user_id=current_user.id
        ).count()
        
        if attempt_count >= exam.max_attempts:
            raise HTTPException(status_code=400, detail="已达到最大答题次数")
        
        submission = await Submission.create(
            exam=exam,
            user=current_user,
            status="in_progress",
            total_score=exam.total_points,
            started_at=datetime.now(),
        )
    
    return templates.TemplateResponse("student/take_exam.html", {
        "request": request,
        "user": current_user,
        "exam": exam,
        "submission": submission,
        "questions": list(exam.questions)
    })


# ===== 提交答案 =====
@router.post("/exam/{exam_id}/submit")
async def submit_exam(
    exam_id: int,
    request: Request,
    current_user: User = Depends(require_student),
    answers_data: str = Form(...)
):
    """提交答案"""
    import json
    
    exam = await Exam.get_or_none(id=exam_id)
    if not exam:
        raise HTTPException(status_code=404, detail="试卷不存在")
    
    submission = await Submission.filter(
        exam_id=exam_id,
        user_id=current_user.id,
        status="in_progress"
    ).first()
    
    if not submission:
        raise HTTPException(status_code=400, detail="没有进行中的答题记录")
    
    # 解析答案
    try:
        answers_dict = json.loads(answers_data)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="答案格式错误")
    
    # 保存答案并自动评分
    total_score = 0
    for q_id, user_answer in answers_dict.items():
        question = await Question.get_or_none(id=int(q_id))
        if question:
            is_correct = question.check_answer(user_answer)
            score = question.points if is_correct else 0
            total_score += score
            
            await Answer.create(
                submission=submission,
                question=question,
                user_answer=str(user_answer),
                is_correct=is_correct,
                score=score,
            )
    
    # 更新提交记录
    submission.status = "submitted"
    submission.submitted_at = datetime.now()
    submission.obtained_score = total_score
    submission.is_passed = total_score >= exam.pass_score
    submission.duration_seconds = int((submission.submitted_at - submission.started_at).total_seconds())
    
    await submission.save()
    
    return RedirectResponse(url=f"/student/exam/{exam_id}/result/{submission.id}", status_code=303)


# ===== 答题结果 =====
@router.get("/exam/{exam_id}/result/{submission_id}", response_class=HTMLResponse)
async def exam_result(exam_id: int, submission_id: int, request: Request, current_user: User = Depends(require_student)):
    """答题结果页面"""
    submission = await Submission.get_or_none(id=submission_id).prefetch_related(
        "exam", "answers__question"
    )
    
    if not submission or submission.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="答题记录不存在")
    
    return templates.TemplateResponse("student/exam_result.html", {
        "request": request,
        "user": current_user,
        "submission": submission,
        "exam": submission.exam
    })


# ===== 历史记录 =====
@router.get("/history", response_class=HTMLResponse)
async def student_history(request: Request, current_user: User = Depends(require_student)):
    """答题历史"""
    submissions = await Submission.filter(user_id=current_user.id).prefetch_related("exam").order_by("-created_at")
    
    return templates.TemplateResponse("student/history.html", {
        "request": request,
        "user": current_user,
        "submissions": submissions
    })
