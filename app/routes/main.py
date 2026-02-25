"""主路由模块

提供前端页面和系统主页。
"""

from flask import Blueprint, render_template, jsonify, current_app, redirect, url_for, request
from flask_login import login_required, current_user

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def index():
    """系统主页"""
    # 已登录用户根据角色显示不同面板
    if current_user.is_authenticated:
        # 管理员跳转到管理面板
        if current_user.is_admin():
            return redirect(url_for('admin.dashboard'))

        # 教师跳转到教师面板
        if current_user.is_teacher():
            return redirect(url_for('teacher.dashboard'))

        # 学生显示学生个人面板
        # 获取用户统计数据
        from app.models import Submission, Answer, Question
        from app.extensions import db
        from sqlalchemy import func

        # 统计总数
        total_exams = db.session.query(func.count(Submission.id)).filter_by(user_id=current_user.id, status='submitted').scalar() or 0
        total_answers = db.session.query(func.count(Answer.id)).join(Submission).filter(Submission.user_id==current_user.id).scalar() or 0

        # 统计平均分
        submitted_exams = Submission.query.filter_by(user_id=current_user.id, status='submitted').all()
        average_score = sum([e.obtained_score or 0 for e in submitted_exams]) / len(submitted_exams) if submitted_exams else 0

        # 统计正确率
        total_answers_list = Answer.query.join(Submission).filter(Submission.user_id==current_user.id).all()
        correct_count = sum([1 for a in total_answers_list if a.is_correct])
        accuracy = (correct_count / len(total_answers_list) * 100) if total_answers_list else 0

        # 最近考试记录
        recent_submissions = Submission.query.filter_by(user_id=current_user.id)\
            .order_by(Submission.submitted_at.desc()).limit(5).all()

        # 为每个submission添加exam_title和accuracy属性
        for sub in recent_submissions:
            if sub.exam:
                sub.exam_title = sub.exam.title
            else:
                sub.exam_title = '未命名考试'

            # 计算本次考试的正确率
            sub_answers = Answer.query.filter_by(submission_id=sub.id).all()
            if sub_answers:
                correct = sum([1 for a in sub_answers if a.is_correct])
                sub.accuracy = (correct / len(sub_answers) * 100)
            else:
                sub.accuracy = 0

        # 薄弱知识点统计
        type_stats = db.session.query(
            Question.type,
            func.count(Answer.id).label('total'),
            func.sum(func.cast(Answer.is_correct, db.Integer)).label('correct')
        ).join(Answer).join(Submission)\
            .filter(Submission.user_id==current_user.id)\
            .group_by(Question.type)\
            .all()

        weak_types = []
        type_name_map = {
            'single_choice': '单选题',
            'multiple_choice': '多选题',
            'true_false': '判断题',
            'fill_blank': '填空题',
            'short_answer': '简答题'
        }
        for type_name, total, correct in type_stats:
            percentage = (correct / total * 100) if total > 0 else 0
            if percentage < 70:
                weak_types.append({
                    'type_name': type_name_map.get(type_name, type_name),
                    'correct_percentage': percentage
                })

        stats = {
            'total_exams': total_exams,
            'total_questions': total_answers,
            'average_score': average_score,
            'accuracy': accuracy,
            'weak_types': weak_types,
            'days_learning': 1  # 暂时固定为1，可根据注册日期计算
        }

        return render_template('student_dashboard.html', stats=stats, recent_submissions=recent_submissions)

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
    """考试页面（已废弃，重定向到真题测试）"""
    return redirect(url_for('main.exam_select_page'))


@main_bp.route('/exam-select')
def exam_select_page():
    """真题测试页面 - 科目-等级-试卷选择"""
    return render_template('student_home.html', current_step=1)


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
        # 安全计算总分，跳过非数值类型的points
        exam.total_score = sum(q.points if isinstance(q.points, (int, float)) else 0 for q in questions)
        
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
        from app.services import SubmissionService, AnswerService, ExamService, QuestionService
        from app.extensions import db
        from app.models import Question, Answer

        submission_service = SubmissionService(db)
        exam_service = ExamService(db)
        question_service = QuestionService(db)
        
        submission = submission_service.get_by_id(submission_id)
        if not submission:
            return render_template('errors/404.html', message='提交记录不存在'), 404
        
        exam = exam_service.get_by_id(submission.exam_id)
        if not exam:
            return render_template('errors/404.html', message='考试不存在'), 404
        
        # 获取考试的所有题目
        all_questions = Question.query.filter_by(exam_id=submission.exam_id).order_by(Question.order_index).all()
        
        # 获取已提交的答案
        existing_answers = Answer.query.filter_by(submission_id=submission_id).all()
        answers_map = {a.question_id: a for a in existing_answers}
        
        # 为每道题创建答案对象（未答的题目会创建空答案）
        all_answers = []
        for question in all_questions:
            if question.id in answers_map:
                all_answers.append(answers_map[question.id])
            else:
                # 创建空的答案对象用于未答题目
                class EmptyAnswer:
                    def __init__(self, question):
                        self.id = None
                        self.question_id = question.id
                        self.user_answer = None
                        self.is_correct = False
                        self.score = 0.0
                        self.question = question
                        self.ai_feedback = None
                all_answers.append(EmptyAnswer(question))
        
        # 统计信息
        correct_count = sum(1 for a in all_answers if a.is_correct)
        incorrect_count = sum(1 for a in all_answers if not a.is_correct and a.user_answer)
        unanswered_count = sum(1 for a in all_answers if not a.user_answer)
        
        # 计算平均得分
        if len(all_answers) > 0:
            average_score = submission.obtained_score / len(all_answers)
        else:
            average_score = 0
        
        # 按题型统计
        type_stats = {}
        for answer in all_answers:
            q_type = answer.question.type if answer.question else 'unknown'
            if q_type not in type_stats:
                type_stats[q_type] = {
                    'type': q_type,
                    'total_count': 0,
                    'correct_count': 0
                }
            type_stats[q_type]['total_count'] += 1
            if answer.is_correct:
                type_stats[q_type]['correct_count'] += 1

        # 计算各题型的正确率
        for stat in type_stats.values():
            if stat['total_count'] > 0:
                stat['correct_percentage'] = (stat['correct_count'] / stat['total_count']) * 100
            else:
                stat['correct_percentage'] = 0

        # 找出薄弱题型（正确率低于60%的题型）
        weak_types = [t for t, s in type_stats.items() if s['correct_percentage'] < 60]

        # 传递给模板的所有数据
        return render_template('submission/result.html',
            submission=submission,
            exam=exam,
            all_answers=all_answers,
            correct_count=correct_count,
            incorrect_count=incorrect_count,
            unanswered_count=unanswered_count,
            average_score=average_score,
            type_stats=sorted(type_stats.values(), key=lambda x: x['correct_percentage'], reverse=True),
            weak_types=weak_types
        )
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
    """文档上传页面（已废弃，请使用试卷管理）"""
    return redirect(url_for('main.exam_manage_page'))


@main_bp.route('/exam-manage')
@login_required
def exam_manage_page():
    """试卷管理页面"""
    from flask import flash
    if not current_user.is_admin():
        flash('您没有权限访问此页面', 'danger')
        return redirect(url_for('main.dashboard'))
    return render_template('admin/exam_manage.html')


@main_bp.route('/submissions')
def submissions_page():
    """提交记录页面"""
    return render_template('submissions.html')


@main_bp.route('/ai-configs')
def ai_configs_page():
    """AI配置管理页面"""
    return render_template('ai_configs.html')


@main_bp.route('/practice')
def practice_page():
    """专项刷题页面"""
    return render_template('practice/index.html')


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


@main_bp.route('/api/subjects', methods=['GET'])
def api_subjects():
    """获取科目列表（公开接口）"""
    from app.models import Subject
    from app.extensions import db

    subjects = Subject.query.filter_by(is_active=True).order_by(Subject.order_index, Subject.name).all()
    return jsonify({
        'success': True,
        'data': [s.to_dict(include_levels=True) for s in subjects]
    })


@main_bp.route('/api/subjects/<int:subject_id>/levels', methods=['GET'])
def api_subject_levels(subject_id):
    """获取指定科目的等级列表（公开接口）"""
    from app.models import Level
    from app.extensions import db

    levels = Level.query.filter_by(subject_id=subject_id, is_active=True).order_by(Level.order_index, Level.name).all()
    return jsonify({
        'success': True,
        'data': [l.to_dict(include_exams=True) for l in levels]
    })