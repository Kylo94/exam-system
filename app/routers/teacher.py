"""
教师路由
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse

from app.auth import require_teacher
from app.models.answer import Answer
from app.models.exam import Exam
from app.models.question import Question
from app.models.student_exam_access import StudentExamAccess
from app.models.subject import Subject
from app.models.submission import Submission
from app.models.teacher_bind_request import TeacherBindRequest
from app.models.user import User
from app.services.exam_access_service import ExamAccessService
from app.services.teacher_bind_service import TeacherBindService
from app.templating import templates

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def teacher_home(request: Request, current_user: User = Depends(require_teacher)):
    """教师首页 - 工作台"""
    from app.models.student_exam_access import StudentExamAccess

    # 获取统计数据
    students_count = await User.filter(teacher_id=current_user.id, role="student").count()
    access_count = await StudentExamAccess.filter(teacher_id=current_user.id).count()

    # 待批改数量（状态为submitted的主观题提交）
    student_ids = await User.filter(teacher_id=current_user.id).values_list("id", flat=True)
    pending_count = await Submission.filter(user_id__in=student_ids, status="submitted").count()

    # 绑定申请数量
    bind_request_count = await TeacherBindRequest.filter(teacher_id=current_user.id, status="pending").count()

    recent_submissions = await Submission.filter(
        user__teacher_id=current_user.id
    ).prefetch_related("user", "exam").order_by("-created_at")[:10]

    return templates.TemplateResponse("teacher/dashboard.html", {
        "request": request,
        "current_user": current_user,
        "stats": {
            "students_count": students_count,
            "access_count": access_count,
            "submissions_count": len(recent_submissions),
            "pending_count": pending_count,
            "bind_request_count": bind_request_count
        },
        "recent_submissions": recent_submissions
    })


# ===== 学生管理 =====
@router.get("/students", response_class=HTMLResponse)
async def teacher_students(request: Request, current_user: User = Depends(require_teacher)):
    """学生列表"""
    students = await User.filter(teacher_id=current_user.id, role="student").order_by("-created_at")

    # 获取每个学生的授权信息
    students_with_access = []
    for student in students:
        accesses = await ExamAccessService.get_student_accesses(student.id)
        students_with_access.append({
            "student": student,
            "accesses": accesses
        })

    return templates.TemplateResponse("teacher/students.html", {
        "request": request,
        "current_user": current_user,
        "students": students,  # 保持向后兼容
        "students_with_access": students_with_access
    })


@router.get("/students/{student_id}/submissions", response_class=HTMLResponse)
async def teacher_student_submissions(
    student_id: int,
    request: Request,
    current_user: User = Depends(require_teacher)
):
    """查看指定学生的答题记录"""
    # 检查学生是否属于该教师
    student = await User.get_or_none(id=student_id, role="student", teacher_id=current_user.id)
    if not student:
        raise HTTPException(status_code=404, detail="学生不存在或无权限")

    submissions = await Submission.filter(user_id=student_id).prefetch_related("user", "exam").order_by("-created_at")

    return templates.TemplateResponse("teacher/submissions.html", {
        "request": request,
        "current_user": current_user,
        "submissions": submissions,
        "students": [student],
        "filters": {"student_id": student_id, "exam_id": None}
    })


# ===== 授权管理 =====
@router.get("/exam-access", response_class=HTMLResponse)
async def exam_access_management(
    request: Request,
    student_id: str = None,
    subject_id: str = None,
    page: int = 1,
    page_size: int = 20,
    current_user: User = Depends(require_teacher)
):
    """试卷授权管理页面"""
    # 转换参数
    student_id_int = int(student_id) if student_id and student_id.isdigit() else None
    subject_id_int = int(subject_id) if subject_id and subject_id.isdigit() else None

    # 获取所有绑定的学生
    students = await User.filter(teacher_id=current_user.id, role="student").order_by("-created_at")

    # 获取所有科目
    subjects = await Subject.all().order_by("name")

    # 构建查询条件
    query = StudentExamAccess.filter(teacher_id=current_user.id)
    if student_id_int:
        query = query.filter(student_id=student_id_int)
    if subject_id_int:
        query = query.filter(subject_id=subject_id_int)

    # 分页
    total = await query.count()
    offset = (page - 1) * page_size
    accesses = await query.prefetch_related("student", "subject", "level").order_by("-granted_at").offset(offset).limit(page_size)

    total_pages = (total + page_size - 1) // page_size if total > 0 else 1

    # 按学生分组
    access_by_student = {}
    for access in accesses:
        sid = access.student_id
        if sid not in access_by_student:
            access_by_student[sid] = []
        access_by_student[sid].append(access)

    return templates.TemplateResponse("teacher/exam_access.html", {
        "request": request,
        "current_user": current_user,
        "students": students,
        "subjects": subjects,
        "access_by_student": access_by_student,
        "accesses": accesses,
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": total_pages
        },
        "filters": {
            "student_id": student_id,  # pass string to preserve form selection
            "subject_id": subject_id
        }
    })


@router.post("/api/exam-access/grant")
async def grant_exam_access(
    request: Request,
    current_user: User = Depends(require_teacher)
):
    """授权学生访问试卷类型"""
    form_data = await request.form()
    student_ids = form_data.getlist("student_ids")
    subject_id = form_data.get("subject_id")
    level_id = form_data.get("level_id")

    if not student_ids or not subject_id:
        return JSONResponse({"success": False, "message": "缺少必要参数"})

    try:
        subject_id = int(subject_id)
        level_id = int(level_id) if level_id and level_id != "0" else None
    except ValueError:
        return JSONResponse({"success": False, "message": "参数格式错误"})

    # 批量授权
    granted = 0
    for sid in student_ids:
        await ExamAccessService.grant_access(
            student_id=int(sid),
            teacher_id=current_user.id,
            subject_id=subject_id,
            level_id=level_id,
            granted_by_id=current_user.id
        )
        granted += 1

    return JSONResponse({"success": True, "granted": granted})


@router.post("/api/exam-access/revoke/{access_id}")
async def revoke_exam_access(
    access_id: int,
    request: Request,
    current_user: User = Depends(require_teacher)
):
    """撤销授权"""
    access = await ExamAccessService.revoke_access(access_id)
    if access:
        return JSONResponse({"success": True})
    return JSONResponse({"success": False, "message": "授权记录不存在"})


# ===== 绑定申请 =====
@router.get("/bind-requests", response_class=HTMLResponse)
async def bind_requests_page(request: Request, current_user: User = Depends(require_teacher)):
    """绑定申请页面"""
    # 获取发给该教师的绑定申请
    bind_requests = await TeacherBindRequest.filter(
        teacher_id=current_user.id,
        status="pending"
    ).prefetch_related("student").order_by("-created_at")

    return templates.TemplateResponse("teacher/bind_requests.html", {
        "request": request,
        "current_user": current_user,
        "bind_requests": bind_requests
    })


@router.get("/api/bind-requests")
async def api_get_teacher_bind_requests(
    request: Request,
    status: str = "pending",
    current_user: User = Depends(require_teacher)
):
    """获取绑定申请列表（API）- 教师端"""
    bind_requests = await TeacherBindRequest.filter(
        teacher_id=current_user.id,
        status=status
    ).prefetch_related("student").order_by("-created_at")

    result = []
    for req in bind_requests:
        result.append({
            "id": req.id,
            "student_name": req.student.username if req.student else "未知",
            "student_email": req.student.email if req.student else "",
            "message": req.message or "",
            "status": req.status,
            "created_at": req.created_at.isoformat() if req.created_at else None
        })

    return JSONResponse(result)


@router.post("/api/bind-requests/{request_id}/approve")
async def approve_bind_request(
    request_id: int,
    request: Request,
    current_user: User = Depends(require_teacher)
):
    """批准绑定申请"""
    try:
        await TeacherBindService.approve_bind_request(request_id, teacher_id=current_user.id)
        return JSONResponse({"success": True})
    except ValueError as e:
        return JSONResponse({"success": False, "message": str(e)})


@router.post("/api/bind-requests/{request_id}/reject")
async def reject_bind_request(
    request_id: int,
    request: Request,
    current_user: User = Depends(require_teacher)
):
    """拒绝绑定申请"""
    try:
        await TeacherBindService.reject_bind_request(request_id, teacher_id=current_user.id)
        return JSONResponse({"success": True})
    except ValueError as e:
        return JSONResponse({"success": False, "message": str(e)})


# ===== 试卷查看（只读）=====
@router.get("/exams", response_class=HTMLResponse)
async def teacher_exams(request: Request, current_user: User = Depends(require_teacher)):
    """可查看的试卷列表（只能查看，不能创建）"""
    # 教师可以查看所有已发布的试卷（由管理员创建）
    exams = await Exam.filter(is_published=True).prefetch_related("subject", "level", "creator").order_by("-created_at")

    return templates.TemplateResponse("teacher/exams.html", {
        "request": request,
        "current_user": current_user,
        "exams": exams
    })


@router.get("/exams/{exam_id}/view", response_class=HTMLResponse)
async def view_exam(exam_id: int, request: Request, current_user: User = Depends(require_teacher)):
    """查看试卷详情（只读）"""
    exam = await Exam.get_or_none(id=exam_id)
    if not exam:
        raise HTTPException(status_code=404, detail="试卷不存在")

    questions = await Question.filter(exam_id=exam_id).order_by("order_num")

    return templates.TemplateResponse("teacher/exam_view.html", {
        "request": request,
        "current_user": current_user,
        "exam": exam,
        "questions": questions
    })


# ===== 成绩查看 =====
@router.get("/submissions", response_class=HTMLResponse)
async def teacher_submissions(
    request: Request,
    student_id: int = None,
    exam_id: int = None,
    current_user: User = Depends(require_teacher)
):
    """答题记录列表"""
    # 获取自己学生的提交记录
    student_ids = await User.filter(teacher_id=current_user.id).values_list("id", flat=True)

    query = Submission.filter(user_id__in=student_ids)

    if student_id:
        query = query.filter(user_id=student_id)
    if exam_id:
        query = query.filter(exam_id=exam_id)

    submissions = await query.prefetch_related("user", "exam").order_by("-created_at")

    # 获取学生列表用于筛选
    students = await User.filter(teacher_id=current_user.id, role="student").order_by("username")

    return templates.TemplateResponse("teacher/submissions.html", {
        "request": request,
        "current_user": current_user,
        "submissions": submissions,
        "students": students,
        "filters": {"student_id": student_id, "exam_id": exam_id}
    })


@router.get("/submissions/{submission_id}", response_class=HTMLResponse)
async def submission_detail(submission_id: int, request: Request, current_user: User = Depends(require_teacher)):
    """答题详情"""
    submission = await Submission.get_or_none(id=submission_id).prefetch_related(
        "user", "exam", "answers", "answers__question"
    )

    if not submission:
        raise HTTPException(status_code=404, detail="提交记录不存在")

    # 检查权限 - 只能查看自己学生的提交
    student = await User.get_or_none(id=submission.user_id)
    if not student or student.teacher_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权限查看此记录")

    # 获取试卷全部题目（按order排序）
    exam = await Exam.get_or_none(id=submission.exam_id).prefetch_related("questions")
    questions = list(exam.questions) if exam else []

    # 构建答案映射 {question_id: answer}
    answer_map = {}
    for answer in submission.answers:
        answer_map[answer.question_id] = answer

    return templates.TemplateResponse("teacher/submission_detail.html", {
        "request": request,
        "current_user": current_user,
        "submission": submission,
        "exam": exam,
        "questions": questions,
        "answer_map": answer_map
    })


# ===== 主观题评分 =====
@router.get("/submissions/{submission_id}/grade", response_class=HTMLResponse)
async def grade_submission_page(submission_id: int, request: Request, current_user: User = Depends(require_teacher)):
    """主观题评分页面"""
    submission = await Submission.get_or_none(id=submission_id).prefetch_related("user", "exam", "answers__question")

    if not submission:
        raise HTTPException(status_code=404, detail="提交记录不存在")

    # 检查权限
    student = await User.get_or_none(id=submission.user_id)
    if not student or student.teacher_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权限查看此记录")

    # 获取需要评分的主观题（简答题和编程题）
    subjective_answers = []
    for answer in submission.answers:
        if answer.question and answer.question.type in ["short_answer", "coding"]:
            subjective_answers.append(answer)

    return templates.TemplateResponse("teacher/grade_submission.html", {
        "request": request,
        "current_user": current_user,
        "submission": submission,
        "subjective_answers": subjective_answers
    })


@router.post("/api/submissions/{submission_id}/grade")
async def grade_submission(
    submission_id: int,
    request: Request,
    current_user: User = Depends(require_teacher)
):
    """提交评分结果"""
    submission = await Submission.get_or_none(id=submission_id)
    if not submission:
        return JSONResponse({"success": False, "message": "提交记录不存在"})

    # 检查权限
    student = await User.get_or_none(id=submission.user_id)
    if not student or student.teacher_id != current_user.id:
        return JSONResponse({"success": False, "message": "无权限"})

    form_data = await request.form()
    scores = {}

    for key, value in form_data.items():
        if key.startswith("score_"):
            answer_id = key.replace("score_", "")
            scores[answer_id] = float(value)

    # 更新答案分数
    total_obtained = 0
    for answer in submission.answers:
        if str(answer.id) in scores:
            answer.score = scores[str(answer.id)]
            await answer.save()
            total_obtained += answer.score

    # 计算总分并更新提交状态
    all_answers = await Answer.filter(submission_id=submission_id).all()
    total_score = sum(a.score for a in all_answers)

    submission.obtained_score = total_score
    submission.status = "graded"
    submission.is_passed = total_score >= submission.exam.pass_score if submission.exam else False
    await submission.save()

    return JSONResponse({"success": True, "obtained_score": total_score})
