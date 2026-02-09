"""主路由模块

提供前端页面和系统主页。
"""

from flask import Blueprint, render_template, jsonify, current_app

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def index():
    """系统主页"""
    return render_template('index.html')


@main_bp.route('/dashboard')
def dashboard():
    """控制面板"""
    return render_template('dashboard.html')


@main_bp.route('/exams')
def exams_page():
    """考试页面"""
    return render_template('exams.html')


@main_bp.route('/subjects')
def subjects_page():
    """科目管理页面"""
    return render_template('subjects.html')


@main_bp.route('/levels')
def levels_page():
    """难度级别管理页面"""
    return render_template('levels.html')


@main_bp.route('/questions')
def questions_page():
    """问题管理页面"""
    return render_template('questions.html')


@main_bp.route('/upload')
def upload_page():
    """文档上传页面"""
    return render_template('upload.html')


@main_bp.route('/submissions')
def submissions_page():
    """提交记录页面"""
    return render_template('submissions.html')


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