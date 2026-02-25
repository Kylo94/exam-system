"""主路由模块

提供前端页面和系统主页。
"""

from flask import Blueprint, render_template, jsonify, current_app, redirect, url_for, request
from flask_login import login_required, current_user

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def index():
    """系统主页"""
    # 已登录用户显示用户主页
    if current_user.is_authenticated:
        return render_template('index.html')
    
    # 未登录用户显示欢迎页面
    return render_template('welcome.html')


@main_bp.route('/dashboard')
@login_required
def dashboard():
    """控制面板"""
    if current_user.is_student():
        return redirect(url_for('main.index'))
    elif current_user.is_teacher():
        return redirect(url_for('teacher.dashboard'))
    # 管理员和其他用户可以访问系统控制面板
    return render_template('dashboard.html')


@main_bp.route('/exams')
def exams_page():
    """考试页面"""
    return render_template('exams.html')


@main_bp.route('/exams/<int:exam_id>')
def exam_detail(exam_id):
    """考试详情页面"""
    try:
        from app.services import ExamService
        from app.extensions import db

        service = ExamService(db)
        exam = service.get_by_id(exam_id)
        
        if not exam:
            return render_template('errors/404.html', message='考试不存在'), 404
        
        return render_template('exam/detail.html', exam=exam)
    except Exception as e:
        return render_template('errors/500.html', message=str(e)), 500


@main_bp.route('/exams/<int:exam_id>/edit')
def exam_edit(exam_id):
    """考试编辑页面"""
    try:
        from app.services import ExamService
        from app.extensions import db

        service = ExamService(db)
        exam = service.get_by_id(exam_id)
        
        if not exam:
            return render_template('errors/404.html', message='考试不存在'), 404
        
        return render_template('exam/edit.html', exam=exam)
    except Exception as e:
        return render_template('errors/500.html', message=str(e)), 500


@main_bp.route('/exams/<int:exam_id>/start', methods=['GET', 'POST'])
def start_exam(exam_id):
    """开始考试"""
    try:
        from app.services import ExamService, SubmissionService
        from app.extensions import db
        from flask_login import current_user

        exam_service = ExamService(db)
        exam = exam_service.get_by_id(exam_id)
        
        if not exam:
            return render_template('errors/404.html', message='考试不存在'), 404
        
        # 检查是否可以开始考试
        user_id = current_user.id if current_user.is_authenticated else 1
        can_start = exam_service.can_start_exam(exam_id, user_id)
        
        if not can_start['can_start']:
            return render_template('exam/cannot_start.html', 
                                   exam=exam, 
                                   reason=can_start.get('reason', '无法开始考试'))
        
        # 如果是POST请求，创建提交记录并跳转到答题页面
        if request.method == 'POST':
            submission_service = SubmissionService(db)
            submission = submission_service.create_submission(
                exam_id=exam_id,
                user_id=user_id
            )
            
            return redirect(url_for('main.take_exam', submission_id=submission.id))
        
        return render_template('exam/start.html', exam=exam)
    except Exception as e:
        return render_template('errors/500.html', message=str(e)), 500


@main_bp.route('/exam/<int:submission_id>')
def take_exam(submission_id):
    """答题页面"""
    try:
        from app.services import SubmissionService, ExamService, QuestionService
        from app.extensions import db

        submission_service = SubmissionService(db)
        exam_service = ExamService(db)
        question_service = QuestionService(db)
        
        submission = submission_service.get_by_id(submission_id)
        if not submission:
            return render_template('errors/404.html', message='考试记录不存在'), 404
        
        exam = exam_service.get_by_id(submission.exam_id)
        if not exam:
            return render_template('errors/404.html', message='考试不存在'), 404
        
        questions = question_service.get_by_exam_id(exam.id)
        
        # 扩展exam对象，添加问题列表
        exam.questions = questions
        exam.question_count = len(questions)
        exam.total_score = sum(q.score for q in questions)
        
        return render_template('exam/take_exam.html', exam=exam, submission=submission)
    except Exception as e:
        return render_template('errors/500.html', message=str(e)), 500


@main_bp.route('/submissions/<int:submission_id>')
def submission_detail(submission_id):
    """提交记录详情页面"""
    try:
        from app.services import SubmissionService, AnswerService
        from app.extensions import db

        submission_service = SubmissionService(db)
        answer_service = AnswerService(db)
        
        submission = submission_service.get_by_id(submission_id)
        if not submission:
            return render_template('errors/404.html', message='提交记录不存在'), 404
        
        answers = answer_service.get_by_submission_id(submission_id)
        
        # 扩展submission对象
        submission.answers = answers
        
        return render_template('submission/detail.html', submission=submission)
    except Exception as e:
        return render_template('errors/500.html', message=str(e)), 500


@main_bp.route('/my-submissions')
def my_submissions():
    """我的考试记录页面"""
    try:
        from flask_login import current_user
        
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login_page'))
        
        return render_template('submission/my_submissions.html')
    except Exception as e:
        return render_template('errors/500.html', message=str(e)), 500


@main_bp.route('/submission/<int:submission_id>/result')
def submission_result(submission_id):
    """考试结果页面"""
    try:
        from app.services import SubmissionService, AnswerService, ExamService
        from app.extensions import db

        submission_service = SubmissionService(db)
        answer_service = AnswerService(db)
        exam_service = ExamService(db)
        
        submission = submission_service.get_by_id(submission_id)
        if not submission:
            return render_template('errors/404.html', message='提交记录不存在'), 404
        
        answers = answer_service.get_by_submission_id(submission_id)
        exam = exam_service.get_by_id(submission.exam_id)
        
        # 统计信息
        correct_count = sum(1 for a in answers if a.is_correct)
        incorrect_count = sum(1 for a in answers if not a.is_correct and a.user_answer)
        unanswered_count = sum(1 for a in answers if not a.user_answer)
        
        # 扩展submission对象
        submission.answers = answers
        submission.exam = exam
        submission.correct_count = correct_count
        submission.incorrect_count = incorrect_count
        submission.unanswered_count = unanswered_count
        
        return render_template('submission/result.html', submission=submission)
    except Exception as e:
        return render_template('errors/500.html', message=str(e)), 500


@main_bp.route('/subjects')
def subjects_page():
    """科目管理页面"""
    return render_template('subjects.html')


@main_bp.route('/subjects/<int:subject_id>/levels')
def subject_levels_page(subject_id):
    """科目等级管理页面"""
    from app.models import Subject
    subject = Subject.query.get(subject_id)
    if not subject:
        return render_template('errors/404.html'), 404

    subject_name = request.args.get('subject_name', subject.name)
    return render_template('subjects/levels.html', subject_id=subject_id, subject_name=subject_name)


@main_bp.route('/levels')
def levels_page():
    """难度级别管理页面（已废弃，请使用科目等级管理）"""
    return render_template('levels.html')


@main_bp.route('/questions')
def questions_page():
    """问题管理页面"""
    return render_template('question/list.html')


@main_bp.route('/questions/create')
def create_question_page():
    """创建题目页面"""
    return render_template('question/create.html')


@main_bp.route('/questions/<int:question_id>/edit')
def edit_question_page(question_id):
    """编辑题目页面"""
    try:
        from app.services import QuestionService
        from app.extensions import db

        service = QuestionService(db)
        question = service.get_by_id(question_id)
        
        if not question:
            return render_template('errors/404.html', message='题目不存在'), 404
        
        return render_template('question/edit.html', question=question)
    except Exception as e:
        return render_template('errors/500.html', message=str(e)), 500


@main_bp.route('/upload')
def upload_page():
    """文档上传页面"""
    return render_template('upload.html')


@main_bp.route('/submissions')
def submissions_page():
    """提交记录页面"""
    return render_template('submissions.html')


@main_bp.route('/ai-configs')
def ai_configs_page():
    """AI配置管理页面"""
    return render_template('ai_configs.html')


@main_bp.route('/api/health')
def health_check():
    """健康检查接口"""
    return jsonify({
        'status': 'healthy',
        'app_name': current_app.config['APP_NAME'],
        'debug': current_app.config['DEBUG']
    })


@main_bp.route('/api/info')
def system_info():
    """系统信息接口"""
    from app.models import Subject, Level, Exam, Question, Submission, Answer
    from app.extensions import db
    
    with db.session() as session:
        stats = {
            'subjects': session.query(Subject).count(),
            'levels': session.query(Level).count(),
            'exams': session.query(Exam).count(),
            'questions': session.query(Question).count(),
            'submissions': session.query(Submission).count(),
            'answers': session.query(Answer).count()
        }
    
    return jsonify({
        'success': True,
        'data': {
            'app_name': current_app.config['APP_NAME'],
            'database_url': current_app.config['SQLALCHEMY_DATABASE_URI'].split('?')[0].split('://')[1] if '://' in current_app.config['SQLALCHEMY_DATABASE_URI'] else current_app.config['SQLALCHEMY_DATABASE_URI'],
            'upload_folder': current_app.config['UPLOAD_FOLDER'],
            'stats': stats
        }
    })