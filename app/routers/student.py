"""
学生路由
"""
import random
from datetime import datetime

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

from app.auth import require_student
from app.models.answer import Answer
from app.models.exam import Exam
from app.models.knowledge_point import KnowledgePoint
from app.models.level import Level
from app.models.question import Question
from app.models.subject import Subject
from app.models.submission import Submission
from app.models.teacher_bind_request import TeacherBindRequest
from app.models.user import User
from app.services.exam_access_service import ExamAccessService
from app.services.wrong_question_service import WrongQuestionService
from app.templating import templates

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def student_home(request: Request, current_user: User = Depends(require_student)):
    """学生首页"""
    from app.models.submission import Submission

    # 获取学生可访问的科目/等级组合
    accessible_subjects = await ExamAccessService.get_student_subjects_with_levels(current_user.id)

    # 获取最近一次答题记录
    last_submission = await Submission.filter(
        user_id=current_user.id,
        status__in=["submitted", "graded"]
    ).order_by("-submitted_at").first()

    # 获取错题数量
    wrong_count = await Submission.filter(user_id=current_user.id).count()  # 简化，实际应该用WrongQuestion

    return templates.TemplateResponse("student/index.html", {
        "request": request,
        "current_user": current_user,
        "accessible_subjects": accessible_subjects,
        "last_submission": last_submission,
        "wrong_count": wrong_count
    })


# ===== 专项刷题 =====
# ===== 按知识点练习 =====
@router.get("/kp-practice", response_class=HTMLResponse)
async def kp_practice_home(request: Request, current_user: User = Depends(require_student)):
    """按知识点练习首页"""
    subjects = await Subject.all().order_by("name")
    return templates.TemplateResponse("student/kp_practice.html", {
        "request": request,
        "current_user": current_user,
        "subjects": subjects
    })


@router.get("/kp-practice/{subject_id}", response_class=HTMLResponse)
async def kp_practice_by_subject(subject_id: int, request: Request, current_user: User = Depends(require_student)):
    """按科目选择知识点练习"""
    subject = await Subject.get_or_none(id=subject_id)
    if not subject:
        raise HTTPException(status_code=404, detail="科目不存在")

    levels = await Level.filter(subject_id=subject_id).order_by("id")
    # 获取每个等级的知识点
    kps_data = []
    for level in levels:
        kps = await KnowledgePoint.filter(level_id=level.id).all()
        # 计算每个知识点的题目数量
        kps_with_count = []
        for kp in kps:
            # 统计主知识点关联的题目数量
            count = await Question.filter(knowledge_point_id=kp.id).count()
            kp.question_count = count
            kps_with_count.append(kp)
        kps_data.append({
            "level": level,
            "kps": kps_with_count
        })

    return templates.TemplateResponse("student/kp_practice_select.html", {
        "request": request,
        "current_user": current_user,
        "subject": subject,
        "kps_data": kps_data
    })


@router.get("/kp-practice/{subject_id}/kp/{kp_id}", response_class=HTMLResponse)
async def kp_practice_questions(
    subject_id: int,
    kp_id: int,
    request: Request,
    current_user: User = Depends(require_student),
    count: int = 10
):
    """按知识点练习题目"""
    subject = await Subject.get_or_none(id=subject_id)
    if not subject:
        raise HTTPException(status_code=404, detail="科目不存在")

    kp = await KnowledgePoint.get_or_none(id=kp_id)
    if not kp:
        raise HTTPException(status_code=404, detail="知识点不存在")

    # 获取该知识点的题目
    questions = await Question.filter(knowledge_point_id=kp_id).limit(count)
    # 随机打乱
    questions = list(questions)
    random.shuffle(questions)

    if not questions:
        return templates.TemplateResponse("student/kp_practice_empty.html", {
            "request": request,
            "current_user": current_user,
            "subject": subject,
            "kp": kp
        })

    return templates.TemplateResponse("student/kp_practice_questions.html", {
        "request": request,
        "current_user": current_user,
        "subject": subject,
        "kp": kp,
        "questions": questions
    })


# ===== 我的试卷 =====
@router.get("/exams", response_class=HTMLResponse)
async def student_exams(request: Request, current_user: User = Depends(require_student)):
    """可参加的试卷列表（按科目和等级分组显示）"""
    # 获取学生可访问的试卷
    accessible_exams = await ExamAccessService.get_accessible_exams(current_user.id)

    # 获取用户已完成的提交记录
    completed_submissions = await Submission.filter(
        user_id=current_user.id,
        status__not="in_progress"
    ).values_list("exam_id", flat=True)
    completed_exam_ids = list(completed_submissions)

    # 获取正在进行中的答题记录
    in_progress_submissions = await Submission.filter(
        user_id=current_user.id,
        status="in_progress"
    ).values_list("exam_id", flat=True)
    in_progress_exam_ids = list(in_progress_submissions)

    # 按科目和等级分组
    grouped = {}  # {subject_id: {subject_name, levels: {level_id: {level_name, exams: []}}}}
    for exam in accessible_exams:
        subject_id = exam.subject_id or 0
        level_id = exam.level_id or 0

        if subject_id not in grouped:
            grouped[subject_id] = {
                "subject_name": exam.subject.name if exam.subject else "未分类",
                "levels": {}
            }

        if level_id not in grouped[subject_id]["levels"]:
            grouped[subject_id]["levels"][level_id] = {
                "level_name": exam.level.name if exam.level else "综合",
                "exams": []
            }

        grouped[subject_id]["levels"][level_id]["exams"].append(exam)

    return templates.TemplateResponse("student/exams.html", {
        "request": request,
        "current_user": current_user,
        "grouped": grouped,
        "completed_exam_ids": completed_exam_ids,
        "in_progress_exam_ids": in_progress_exam_ids
    })


# ===== 答题页面 =====
@router.get("/exam/{exam_id}/take", response_class=HTMLResponse)
async def take_exam(exam_id: int, request: Request, current_user: User = Depends(require_student)):
    """答题页面"""
    # 检查学生是否有权访问此试卷
    has_access = await ExamAccessService.check_student_has_access(current_user.id, exam_id)
    if not has_access:
        raise HTTPException(status_code=403, detail="您没有权限访问此试卷")

    exam = await Exam.get_or_none(id=exam_id).prefetch_related("subject", "questions")

    if not exam:
        raise HTTPException(status_code=404, detail="试卷不存在")

    # 获取或创建答题记录
    submission = await Submission.filter(
        exam_id=exam_id,
        user_id=current_user.id,
        status="in_progress"
    ).prefetch_related("answers").first()

    is_new_submission = False
    if not submission:
        submission = await Submission.create(
            exam=exam,
            user=current_user,
            status="in_progress",
            total_score=exam.total_points,
            started_at=datetime.now(),
        )
        is_new_submission = True

    # 构建已选答案映射 {question_id: user_answer}
    existing_answers = {}
    if not is_new_submission:
        for answer in submission.answers:
            existing_answers[str(answer.question_id)] = answer.user_answer

    # 计算剩余时间
    remaining_seconds = None
    if submission.started_at:
        started = submission.started_at
        if started.tzinfo:
            started = started.replace(tzinfo=None)
        elapsed = (datetime.now().replace(tzinfo=None) - started).total_seconds()
        total_seconds = exam.duration_minutes * 60
        remaining = total_seconds - elapsed
        remaining_seconds = max(0, int(remaining))

    return templates.TemplateResponse("student/take_exam.html", {
        "request": request,
        "current_user": current_user,
        "exam": exam,
        "submission": submission,
        "questions": list(exam.questions),
        "existing_answers": existing_answers,
        "remaining_seconds": remaining_seconds
    })


# ===== 自动保存答案 =====
@router.post("/exam/{exam_id}/autosave")
async def autosave_exam(
    exam_id: int,
    request: Request,
    current_user: User = Depends(require_student)
):
    """自动保存答题进度"""
    from fastapi.responses import JSONResponse

    body = await request.json()
    answers_data = body.get("answers", {})

    exam = await Exam.get_or_none(id=exam_id)
    if not exam:
        return JSONResponse({"success": False, "message": "试卷不存在"})

    # 获取进行中的答题记录
    submission = await Submission.filter(
        exam_id=exam_id,
        user_id=current_user.id,
        status="in_progress"
    ).first()

    if not submission:
        return JSONResponse({"success": False, "message": "没有进行中的答题记录"})

    # 删除旧答案，重新保存
    await Answer.filter(submission_id=submission.id).delete()

    # 保存新答案
    saved_count = 0
    import json
    for q_id, user_answer in answers_data.items():
        # 如果答案是数组，转为JSON字符串存储
        if isinstance(user_answer, list):
            user_answer_str = json.dumps(user_answer)
        else:
            user_answer_str = str(user_answer)

        # 直接使用 question_id 而不是 Question 对象
        await Answer.create(
            submission_id=submission.id,
            question_id=int(q_id),
            user_answer=user_answer_str,
            order_num=saved_count + 1,
        )
        saved_count += 1

    return JSONResponse({"success": True, "saved": saved_count})


# ===== 提交答案 =====
@router.post("/exam/{exam_id}/submit")
async def submit_exam(
    exam_id: int,
    request: Request,
    current_user: User = Depends(require_student)
):
    """提交答案"""
    # 停止自动保存
    # 获取进行中的答题记录

    body = await request.json()
    answers_data = body.get("answers", {})

    exam = await Exam.get_or_none(id=exam_id)
    if not exam:
        return JSONResponse({"success": False, "message": "试卷不存在"})

    submission = await Submission.filter(
        exam_id=exam_id,
        user_id=current_user.id,
        status="in_progress"
    ).first()

    if not submission:
        return JSONResponse({"success": False, "message": "没有进行中的答题记录"})

    # 保存答案并自动评分
    total_score = 0
    answers_to_record = []

    import json
    for q_id, user_answer in answers_data.items():
        question = await Question.get_or_none(id=int(q_id))
        if question:
            # 转换答案格式：如果是数组，按题型转为字符串
            if isinstance(user_answer, list):
                if question.type == "multiple_choice":
                    user_answer_str = ",".join(user_answer)
                elif question.type in ["single_choice", "true_false"]:
                    user_answer_str = user_answer[0] if user_answer else ""
                else:
                    user_answer_str = json.dumps(user_answer)
            else:
                user_answer_str = str(user_answer)

            is_correct = question.check_answer(user_answer_str)
            score = question.points if is_correct else 0
            total_score += score

            _answer_record = await Answer.create(
                submission=submission,
                question=question,
                user_answer=user_answer_str,
                is_correct=is_correct,
                score=score,
            )
            answers_to_record.append({
                "question_id": question.id,
                "student_answer": user_answer_str,
                "is_correct": is_correct
            })

    # 更新提交记录
    submission.status = "submitted"
    submission.submitted_at = datetime.now().replace(tzinfo=None)
    submission.obtained_score = total_score
    submission.is_passed = total_score >= exam.pass_score
    # 统一为无时区信息再计算
    started = submission.started_at
    if started.tzinfo:
        started = started.replace(tzinfo=None)
    submission.duration_seconds = int((submission.submitted_at - started).total_seconds())

    await submission.save()

    # 记录错题
    await WrongQuestionService.record_from_submission(submission, answers_to_record)

    return JSONResponse({"success": True, "submission_id": submission.id, "score": total_score})


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
        "current_user": current_user,
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
        "current_user": current_user,
        "submissions": submissions
    })


# ===== 错题库 =====
@router.get("/wrong-questions", response_class=HTMLResponse)
async def wrong_questions_page(
    request: Request,
    subject_id: int = None,
    current_user: User = Depends(require_student)
):
    """错题库页面"""
    wrong_questions = await WrongQuestionService.get_student_wrong_questions(
        student_id=current_user.id,
        subject_id=subject_id
    )

    # 获取所有科目用于筛选
    subjects = await Subject.all().order_by("name")

    return templates.TemplateResponse("student/wrong_questions.html", {
        "request": request,
        "current_user": current_user,
        "wrong_questions": wrong_questions,
        "subjects": subjects,
        "selected_subject_id": subject_id
    })


@router.get("/wrong-questions/practice", response_class=HTMLResponse)
async def wrong_questions_practice(
    request: Request,
    subject_id: int = None,
    current_user: User = Depends(require_student)
):
    """错题练习页面"""
    if subject_id:
        questions = await WrongQuestionService.get_practice_questions(current_user.id, subject_id)
    else:
        # 获取所有错题
        wqs = await WrongQuestionService.get_student_wrong_questions(current_user.id, limit=20)
        questions = [wq.question for wq in wqs if wq.question]

    if not questions:
        return templates.TemplateResponse("student/kp_practice_empty.html", {
            "request": request,
            "current_user": current_user,
            "subject": None,
            "kp": None
        })

    subject = questions[0].exam.subject if questions[0].exam else None

    return templates.TemplateResponse("student/kp_practice_questions.html", {
        "request": request,
        "current_user": current_user,
        "subject": subject,
        "kp": None,  # 错题练习没有特定知识点
        "questions": questions
    })


# ===== 绑定教师 =====
@router.get("/bind-teacher", response_class=HTMLResponse)
async def bind_teacher_page(request: Request, current_user: User = Depends(require_student)):
    """申请绑定教师页面"""
    # 获取所有教师
    teachers = await User.filter(role="teacher", is_active=True).order_by("username")

    # 检查当前绑定状态 - 需要prefetch teacher关系
    current_bind = await TeacherBindRequest.filter(
        student_id=current_user.id
    ).prefetch_related("teacher").order_by("-created_at").first()

    return templates.TemplateResponse("student/bind_teacher.html", {
        "request": request,
        "current_user": current_user,
        "teachers": teachers,
        "current_bind": current_bind
    })


@router.post("/bind-teacher/apply")
async def apply_bind_teacher(
    request: Request,
    teacher_id: int = Form(...),
    message: str = Form(""),
    current_user: User = Depends(require_student)
):
    """申请绑定教师"""
    # 检查是否已经有待处理或已通过的申请
    existing = await TeacherBindRequest.filter(
        student_id=current_user.id,
        status__in=["pending", "approved"]
    ).first()
    if existing:
        if existing.status == "approved":
            raise HTTPException(status_code=400, detail="您已经绑定了一位教师，无法再次申请")
        raise HTTPException(status_code=400, detail="您已有待处理的绑定申请")

    # 检查教师是否存在
    teacher = await User.get_or_none(id=teacher_id, role="teacher")
    if not teacher:
        raise HTTPException(status_code=404, detail="教师不存在")

    # 创建绑定申请
    await TeacherBindRequest.create(
        student_id=current_user.id,
        teacher_id=teacher_id,
        message=message
    )

    return RedirectResponse(url="/student/bind-teacher?success=1", status_code=303)


@router.post("/bind-teacher/cancel")
async def cancel_bind_request(
    request: Request,
    current_user: User = Depends(require_student)
):
    """取消绑定申请"""
    # 删除待处理的申请
    pending = await TeacherBindRequest.filter(student_id=current_user.id, status="pending").first()
    if pending:
        await pending.delete()

    return RedirectResponse(url="/student/bind-teacher", status_code=303)
