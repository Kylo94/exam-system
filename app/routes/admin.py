"""后台管理路由模块

提供管理员专用的管理界面，包括用户管理、科目管理、等级管理、试卷管理、题目管理和提交管理。
"""

from functools import wraps
from flask import Blueprint, request, render_template, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from sqlalchemy import desc, asc

from app.extensions import db
from app.models.user import User
from app.models.subject import Subject
from app.models.level import Level
from app.models.exam import Exam
from app.models.question import Question
from app.models.submission import Submission
from app.utils.response_utils import (
    error_response, success_response, api_response, validation_error_response
)
from app.utils.validators import (
    validate_string, validate_email, validate_password, validate_choice, batch_validate
)

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


def admin_required(f):
    """管理员权限装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login_page', next=request.url))
        if not current_user.is_admin():
            flash('您没有权限访问此页面', 'danger')
            return redirect(url_for('main.dashboard'))
        return f(*args, **kwargs)
    return decorated_function


# ==================== 页面路由 ====================

@admin_bp.route('/')
@login_required
@admin_required
def dashboard():
    """管理仪表板"""
    # 统计信息
    stats = {
        'total_users': User.query.count(),
        'total_subjects': Subject.query.count(),
        'total_levels': Level.query.count(),
        'total_exams': Exam.query.count(),
        'total_questions': Question.query.count(),
        'total_submissions': Submission.query.count(),
        'active_users': User.query.filter_by(is_active=True).count(),
        'recent_submissions': Submission.query.order_by(desc(Submission.created_at)).limit(10).all()
    }
    
    return render_template('admin/dashboard.html', stats=stats)


@admin_bp.route('/users')
@login_required
@admin_required
def users_page():
    """用户管理页面"""
    users = User.query.order_by(desc(User.created_at)).all()
    return render_template('admin/users.html', users=users)


@admin_bp.route('/subjects')
@login_required
@admin_required
def subjects_page():
    """科目管理页面"""
    subjects = Subject.query.order_by(asc(Subject.name)).all()
    return render_template('admin/subjects.html', subjects=subjects)


@admin_bp.route('/levels')
@login_required
@admin_required
def levels_page():
    """等级管理页面"""
    levels = Level.query.order_by(asc(Level.name)).all()
    return render_template('admin/levels.html', levels=levels)


@admin_bp.route('/exams')
@login_required
@admin_required
def exams_page():
    """试卷管理页面"""
    exams = Exam.query.order_by(desc(Exam.created_at)).all()
    return render_template('admin/exams.html', exams=exams)


@admin_bp.route('/questions')
@login_required
@admin_required
def questions_page():
    """题目管理页面"""
    questions = Question.query.order_by(desc(Question.created_at)).all()
    return render_template('admin/questions.html', questions=questions)


@admin_bp.route('/submissions')
@login_required
@admin_required
def submissions_page():
    """提交管理页面"""
    submissions = Submission.query.order_by(desc(Submission.created_at)).all()
    return render_template('admin/submissions.html', submissions=submissions)


# ==================== API路由 ====================

@admin_bp.route('/api/users', methods=['GET'])
@login_required
@admin_required
@api_response
def get_users():
    """获取用户列表API
    
    Query Parameters:
        page: 页码（可选，默认1）
        per_page: 每页数量（可选，默认20）
        role: 按角色过滤（可选）
        is_active: 按激活状态过滤（可选）
        search: 搜索关键词（用户名或邮箱）
        
    Returns:
        用户列表
    """
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    role = request.args.get('role', None)
    is_active = request.args.get('is_active', None)
    search = request.args.get('search', '').strip()
    
    # 构建查询
    query = User.query
    
    if role:
        query = query.filter_by(role=role)
    
    if is_active is not None:
        query = query.filter_by(is_active=is_active.lower() == 'true')
    
    if search:
        query = query.filter(
            db.or_(
                User.username.ilike(f'%{search}%'),
                User.email.ilike(f'%{search}%')
            )
        )
    
    # 分页
    pagination = query.order_by(desc(User.created_at)).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    users = pagination.items
    
    return {
        'users': [user.to_dict(include_sensitive=True) for user in users],
        'pagination': {
            'page': pagination.page,
            'per_page': pagination.per_page,
            'total': pagination.total,
            'pages': pagination.pages,
            'has_next': pagination.has_next,
            'has_prev': pagination.has_prev
        }
    }, 200


@admin_bp.route('/api/users/<int:user_id>', methods=['GET'])
@login_required
@admin_required
@api_response
def get_user(user_id):
    """获取单个用户详情API
    
    Args:
        user_id: 用户ID
        
    Returns:
        用户详情
    """
    user = User.get_by_id(user_id)
    if not user:
        return error_response('用户不存在', 404)
    
    return {
        'user': user.to_dict(include_sensitive=True)
    }, 200


@admin_bp.route('/api/users', methods=['POST'])
@login_required
@admin_required
@api_response
def create_user():
    """创建用户API
    
    Request JSON:
        username: 用户名
        email: 邮箱地址
        password: 密码
        role: 用户角色（admin/teacher/student）
        is_active: 是否激活（可选，默认true）
        
    Returns:
        创建的用户信息
    """
    data = request.get_json()
    if not data:
        return error_response('请求数据不能为空', 400)
    
    # 验证必填字段
    required_fields = ['username', 'email', 'password', 'role']
    for field in required_fields:
        if field not in data:
            return error_response(f'缺少必填字段: {field}', 400)
    
    username = data.get('username', '').strip()
    email = data.get('email', '').strip().lower()
    password = data.get('password', '').strip()
    role = data.get('role', '').strip()
    is_active = data.get('is_active', True)
    
    # 验证输入
    validators = {
        'username': (validate_string, {'field_name': '用户名', 'min_length': 3, 'max_length': 20, 'allow_empty': False}),
        'email': (validate_email, {'field_name': '邮箱地址', 'allow_none': False}),
        'password': (validate_password, {'field_name': '密码', 'min_length': 6, 'max_length': 50, 'allow_empty': False}),
        'role': (validate_choice, {'field_name': '用户角色', 'choices': ['admin', 'teacher', 'student'], 'allow_none': False})
    }
    
    validation_result = batch_validate(data, validators)
    if not validation_result['is_valid']:
        return validation_error_response(validation_result['errors'])
    
    # 检查用户名和邮箱是否已存在
    if User.get_by_username(username):
        return error_response('用户名已存在', 400)
    
    if User.get_by_email(email):
        return error_response('邮箱地址已存在', 400)
    
    # 创建用户
    try:
        user = User(
            username=username,
            email=email,
            password=password,
            role=role,
            is_active=is_active
        )
        db.session.add(user)
        db.session.commit()
        
        return {
            'user': user.to_dict(include_sensitive=True),
            'message': '用户创建成功'
        }, 201
    except Exception as e:
        db.session.rollback()
        return error_response(f'创建用户失败: {str(e)}', 500)


@admin_bp.route('/api/users/<int:user_id>', methods=['PUT'])
@login_required
@admin_required
@api_response
def update_user(user_id):
    """更新用户API
    
    Args:
        user_id: 用户ID
        
    Request JSON:
        username: 用户名（可选）
        email: 邮箱地址（可选）
        role: 用户角色（可选）
        is_active: 是否激活（可选）
        profile: 用户配置文件（可选）
        
    Returns:
        更新后的用户信息
    """
    user = User.get_by_id(user_id)
    if not user:
        return error_response('用户不存在', 404)
    
    data = request.get_json()
    if not data:
        return error_response('请求数据不能为空', 400)
    
    # 更新字段
    if 'username' in data:
        username = data.get('username', '').strip()
        if username and username != user.username:
            if User.get_by_username(username):
                return error_response('用户名已存在', 400)
            user.username = username
    
    if 'email' in data:
        email = data.get('email', '').strip().lower()
        if email and email != user.email:
            if User.get_by_email(email):
                return error_response('邮箱地址已存在', 400)
            user.email = email
    
    if 'role' in data:
        role = data.get('role', '').strip()
        if role and role != user.role:
            if role not in ['admin', 'teacher', 'student']:
                return error_response('用户角色无效', 400)
            user.role = role
    
    if 'is_active' in data:
        user.is_active = bool(data.get('is_active'))
    
    if 'profile' in data:
        user.profile = data.get('profile')
    
    # 更新密码（如果有）
    if 'password' in data and data['password']:
        password = data.get('password', '').strip()
        is_valid, error_msg = validate_password(password, '密码', min_length=6, max_length=50, allow_empty=False)
        if not is_valid:
            return error_response(error_msg, 400)
        user.set_password(password)
    
    try:
        db.session.commit()
        return {
            'user': user.to_dict(include_sensitive=True),
            'message': '用户更新成功'
        }, 200
    except Exception as e:
        db.session.rollback()
        return error_response(f'更新用户失败: {str(e)}', 500)


@admin_bp.route('/api/users/<int:user_id>', methods=['DELETE'])
@login_required
@admin_required
@api_response
def delete_user(user_id):
    """删除用户API
    
    Args:
        user_id: 用户ID
        
    Returns:
        删除成功信息
    """
    user = User.get_by_id(user_id)
    if not user:
        return error_response('用户不存在', 404)
    
    # 防止删除自己
    if user.id == current_user.id:
        return error_response('不能删除当前登录的用户', 400)
    
    try:
        db.session.delete(user)
        db.session.commit()
        return {
            'message': '用户删除成功'
        }, 200
    except Exception as e:
        db.session.rollback()
        return error_response(f'删除用户失败: {str(e)}', 500)


@admin_bp.route('/api/users/<int:user_id>/toggle-active', methods=['POST'])
@login_required
@admin_required
@api_response
def toggle_user_active(user_id):
    """切换用户激活状态API
    
    Args:
        user_id: 用户ID
        
    Returns:
        更新后的用户信息
    """
    user = User.get_by_id(user_id)
    if not user:
        return error_response('用户不存在', 404)
    
    # 防止停用自己
    if user.id == current_user.id:
        return error_response('不能停用当前登录的用户', 400)
    
    user.is_active = not user.is_active
    
    try:
        db.session.commit()
        return {
            'user': user.to_dict(include_sensitive=True),
            'message': f'用户已{"激活" if user.is_active else "停用"}'
        }, 200
    except Exception as e:
        db.session.rollback()
        return error_response(f'更新用户状态失败: {str(e)}', 500)


# 其他实体的API路由可以后续添加（科目、等级、试卷、题目、提交等）

@admin_bp.route('/api/stats', methods=['GET'])
@login_required
@admin_required
@api_response
def get_stats():
    """获取管理统计信息API
    
    Returns:
        统计信息
    """
    stats = {
        'total_users': User.query.count(),
        'total_subjects': Subject.query.count(),
        'total_levels': Level.query.count(),
        'total_exams': Exam.query.count(),
        'total_questions': Question.query.count(),
        'total_submissions': Submission.query.count(),
        'active_users': User.query.filter_by(is_active=True).count(),
        'users_by_role': {
            'admin': User.query.filter_by(role='admin').count(),
            'teacher': User.query.filter_by(role='teacher').count(),
            'student': User.query.filter_by(role='student').count()
        }
    }
    
    return {
        'stats': stats,
        'message': '统计信息获取成功'
    }, 200