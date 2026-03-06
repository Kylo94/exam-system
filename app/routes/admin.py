"""后台管理路由模块

提供管理员专用的管理界面，包括用户管理、科目管理、等级管理、试卷管理、题目管理和提交管理。
"""

from functools import wraps
import os
import uuid
from pathlib import Path
from flask import Blueprint, request, render_template, redirect, url_for, flash, jsonify, current_app
from flask_login import login_required, current_user
from sqlalchemy import desc, asc
from werkzeug.utils import secure_filename

from app.extensions import db
from app.models.user import User
from app.models.subject import Subject
from app.models.level import Level
from app.models.exam import Exam
from app.models.question import Question
from app.models.submission import Submission
from app.utils.response_utils import (
    error_response, success_response, api_response, validation_error_response, pagination_response
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


@admin_bp.route('/knowledge-points')
@login_required
@admin_required
def knowledge_points_page():
    """考点管理页面"""
    return render_template('admin/knowledge_points.html')


@admin_bp.route('/submissions')
@login_required
@admin_required
def submissions_page():
    """提交管理页面"""
    submissions = Submission.query.order_by(desc(Submission.created_at)).all()
    return render_template('admin/submissions.html', submissions=submissions)


@admin_bp.route('/ai-configs')
@login_required
@admin_required
def ai_configs_page():
    """AI配置管理页面"""
    return render_template('ai_configs.html')


@admin_bp.route('/exams')
@login_required
@admin_required
def exams_page():
    """试卷管理页面"""
    return render_template('admin/exam_manage.html')


@admin_bp.route('/exams/<int:exam_id>/edit')
@login_required
@admin_required
def exam_edit_page(exam_id):
    """试卷编辑页面"""
    from app.services import ExamService
    service = ExamService(db)
    exam = service.get_by_id(exam_id)

    if not exam:
        return render_template('errors/404.html', message='试卷不存在'), 404

    return render_template('exam_edit.html', exam_id=exam_id)


@admin_bp.route('/questions')
@login_required
@admin_required
def questions_page():
    """题目管理页面"""
    return render_template('question/list.html')


@admin_bp.route('/questions/create')
@login_required
@admin_required
def create_question_page():
    """创建题目页面"""
    return render_template('question/create.html')


@admin_bp.route('/questions/<int:question_id>/edit')
@login_required
@admin_required
def edit_question_page(question_id):
    """编辑题目页面"""
    from app.services import QuestionService
    service = QuestionService(db)
    question = service.get_by_id(question_id)

    if not question:
        return render_template('errors/404.html', message='题目不存在'), 404

    return render_template('question/edit.html', question=question)


@admin_bp.route('/upload')
@login_required
@admin_required
def upload_page():
    """试卷上传页面"""
    return render_template('upload.html')


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

    return pagination_response(
        items=[user.to_dict(include_sensitive=True) for user in users],
        total=pagination.total,
        page=pagination.page,
        per_page=pagination.per_page,
        message="查询成功"
    )


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

    return success_response(data=user.to_dict(include_sensitive=True))


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
        'password': (validate_password, {'field_name': '密码', 'allow_none': False}),
        'role': (validate_choice, {'choices': ['admin', 'teacher', 'student'], 'field_name': '用户角色', 'allow_none': False})
    }
    
    validation_errors = batch_validate(validators, data)
    if validation_errors:
        return validation_error_response(validation_errors)
    
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
        
        user_dict = user.to_dict(include_sensitive=True)
        print(f"DEBUG: user_dict = {user_dict}")

        return success_response(data=user_dict, message="用户创建成功")
    except Exception as e:
        db.session.rollback()
        import traceback
        traceback.print_exc()
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
        is_valid, error_msg = validate_password(password, '密码')
        if not is_valid:
            return error_response(error_msg, 400)
        user.set_password(password)

    try:
        db.session.commit()
        # 刷新以获取最新的数据
        db.session.refresh(user)
        return success_response(data=user.to_dict(include_sensitive=True), message="用户更新成功")
    except Exception as e:
        db.session.rollback()
        import traceback
        traceback.print_exc()
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
        return success_response(message="用户删除成功")
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
        return success_response(
            data=user.to_dict(include_sensitive=True),
            message=f'用户已{"激活" if user.is_active else "停用"}'
        )
    except Exception as e:
        db.session.rollback()
        return error_response(f'更新用户状态失败: {str(e)}', 500)


# ==================== 科目管理API ====================

@admin_bp.route('/api/subjects', methods=['GET'])
@login_required
@admin_required
@api_response
def get_subjects():
    """获取科目列表API

    Query Parameters:
        page: 页码（可选，默认1）
        per_page: 每页数量（可选，默认20）
        search: 搜索关键词（可选）

    Returns:
        科目列表
    """
    from app.utils.response_utils import pagination_response
    from sqlalchemy import or_

    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    search = request.args.get('search', '').strip()

    # 构建查询
    query = Subject.query

    if search:
        query = query.filter(
            or_(
                Subject.name.ilike(f'%{search}%'),
                Subject.description.ilike(f'%{search}%')
            )
        )

    # 分页
    pagination = query.order_by(Subject.order_index, Subject.name).paginate(
        page=page, per_page=per_page, error_out=False
    )

    subjects = pagination.items

    # 构建科目数据，包含试卷数量
    subjects_data = []
    for subject in subjects:
        subject_dict = subject.to_dict()
        subject_dict['exam_count'] = subject.exams.count()
        subjects_data.append(subject_dict)

    return pagination_response(
        items=subjects_data,
        total=pagination.total,
        page=pagination.page,
        per_page=pagination.per_page,
        message="查询成功"
    )


@admin_bp.route('/api/subjects/<int:subject_id>', methods=['GET'])
@login_required
@admin_required
@api_response
def get_subject(subject_id):
    """获取单个科目详情API

    Args:
        subject_id: 科目ID

    Returns:
        科目详情
    """
    from app.utils.response_utils import success_response

    subject = Subject.get_by_id(subject_id)
    if not subject:
        return error_response('科目不存在', 404)

    subject_dict = subject.to_dict()
    subject_dict['exam_count'] = subject.exams.count()

    return success_response(data=subject_dict, message="查询成功")


@admin_bp.route('/api/subjects', methods=['POST'])
@login_required
@admin_required
@api_response
def create_subject():
    """创建科目API

    Request JSON:
        name: 科目名称
        description: 科目描述（可选）
        order_index: 排序索引（可选）
        is_active: 是否激活（可选，默认true）

    Returns:
        创建的科目信息
    """
    data = request.get_json()
    if not data:
        return error_response('请求数据不能为空', 400)

    # 验证必填字段
    required_fields = ['name']
    for field in required_fields:
        if field not in data:
            return error_response(f'缺少必填字段: {field}', 400)

    name = data.get('name', '').strip()
    description = data.get('description', '').strip()
    order_index = data.get('order_index', 0)
    is_active = data.get('is_active', True)

    # 验证输入
    is_valid, error_msg = validate_string(name, '科目名称', min_length=1, max_length=50, allow_empty=False)
    if not is_valid:
        return error_response(error_msg, 400)

    # 检查名称是否已存在
    if Subject.get_by_name(name):
        return error_response('科目名称已存在', 400)

    try:
        subject = Subject(
            name=name,
            description=description,
            order_index=order_index,
            is_active=is_active
        )
        db.session.add(subject)
        db.session.commit()

        return success_response(data=subject.to_dict(), message="科目创建成功")
    except Exception as e:
        db.session.rollback()
        return error_response(f'创建科目失败: {str(e)}', 500)


@admin_bp.route('/api/subjects/<int:subject_id>', methods=['PUT'])
@login_required
@admin_required
@api_response
def update_subject(subject_id):
    """更新科目API

    Args:
        subject_id: 科目ID

    Request JSON:
        name: 科目名称（可选）
        description: 科目描述（可选）
        order_index: 排序索引（可选）
        is_active: 是否激活（可选）

    Returns:
        更新后的科目信息
    """
    subject = Subject.get_by_id(subject_id)
    if not subject:
        return error_response('科目不存在', 404)

    data = request.get_json()
    if not data:
        return error_response('请求数据不能为空', 400)

    # 更新字段
    if 'name' in data:
        name = data.get('name', '').strip()
        if name and name != subject.name:
            if Subject.get_by_name(name):
                return error_response('科目名称已存在', 400)
            subject.name = name

    if 'description' in data:
        subject.description = data.get('description', '').strip()

    if 'order_index' in data:
        subject.order_index = data.get('order_index', 0)

    if 'is_active' in data:
        subject.is_active = bool(data.get('is_active'))

    try:
        db.session.commit()
        return success_response(data=subject.to_dict(), message="科目更新成功")
    except Exception as e:
        db.session.rollback()
        return error_response(f'更新科目失败: {str(e)}', 500)


@admin_bp.route('/api/subjects/<int:subject_id>', methods=['DELETE'])
@login_required
@admin_required
@api_response
def delete_subject(subject_id):
    """删除科目API

    Args:
        subject_id: 科目ID

    Returns:
        删除成功信息
    """
    subject = Subject.get_by_id(subject_id)
    if not subject:
        return error_response('科目不存在', 404)

    try:
        db.session.delete(subject)
        db.session.commit()
        return success_response(message="科目删除成功")
    except Exception as e:
        db.session.rollback()
        return error_response(f'删除科目失败: {str(e)}', 500)


# ==================== 等级管理API ====================

@admin_bp.route('/api/levels', methods=['GET'])
@login_required
@admin_required
@api_response
def get_levels():
    """获取等级列表API

    Query Parameters:
        page: 页码（可选，默认1）
        per_page: 每页数量（可选，默认20）
        subject_id: 按科目ID过滤（可选）
        search: 搜索关键词（可选）

    Returns:
        等级列表
    """
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    subject_id = request.args.get('subject_id', None)
    search = request.args.get('search', '').strip()

    # 构建查询
    query = Level.query

    if subject_id:
        query = query.filter_by(subject_id=subject_id)

    if search:
        query = query.filter(
            db.or_(
                Level.name.ilike(f'%{search}%'),
                Level.description.ilike(f'%{search}%')
            )
        )

    # 分页
    pagination = query.order_by(Level.order_index, Level.name).paginate(
        page=page, per_page=per_page, error_out=False
    )

    levels = pagination.items

    return pagination_response(
        items=[level.to_dict() for level in levels],
        total=pagination.total,
        page=pagination.page,
        per_page=pagination.per_page,
        message="查询成功"
    )


@admin_bp.route('/api/levels/<int:level_id>', methods=['GET'])
@login_required
@admin_required
@api_response
def get_level(level_id):
    """获取单个等级详情API

    Args:
        level_id: 等级ID

    Returns:
        等级详情
    """
    level = Level.get_by_id(level_id)
    if not level:
        return error_response('等级不存在', 404)

    return success_response(data=level.to_dict(include_exams=True))


@admin_bp.route('/api/levels', methods=['POST'])
@login_required
@admin_required
@api_response
def create_level():
    """创建等级API

    Request JSON:
        subject_id: 所属科目ID
        name: 等级名称
        description: 等级描述（可选）
        order_index: 排序索引（可选）
        is_active: 是否激活（可选，默认true）

    Returns:
        创建的等级信息
    """
    data = request.get_json()
    if not data:
        return error_response('请求数据不能为空', 400)

    # 验证必填字段
    required_fields = ['subject_id', 'name']
    for field in required_fields:
        if field not in data:
            return error_response(f'缺少必填字段: {field}', 400)

    subject_id = data.get('subject_id')
    name = data.get('name', '').strip()
    description = data.get('description', '').strip()
    order_index = data.get('order_index', 0)
    is_active = data.get('is_active', True)

    # 验证输入
    is_valid, error_msg = validate_string(name, '等级名称', min_length=1, max_length=50, allow_empty=False)
    if not is_valid:
        return error_response(error_msg, 400)

    # 检查科目是否存在
    if not Subject.get_by_id(subject_id):
        return error_response('科目不存在', 400)

    # 检查名称是否已存在
    if Level.get_by_name(name):
        return error_response('等级名称已存在', 400)

    try:
        level = Level(
            subject_id=subject_id,
            name=name,
            description=description,
            order_index=order_index,
            is_active=is_active
        )
        db.session.add(level)
        db.session.commit()

        return success_response(data=level.to_dict(), message="等级创建成功")
    except Exception as e:
        db.session.rollback()
        return error_response(f'创建等级失败: {str(e)}', 500)


@admin_bp.route('/api/levels/<int:level_id>', methods=['PUT'])
@login_required
@admin_required
@api_response
def update_level(level_id):
    """更新等级API

    Args:
        level_id: 等级ID

    Request JSON:
        name: 等级名称（可选）
        description: 等级描述（可选）
        order_index: 排序索引（可选）
        is_active: 是否激活（可选）

    Returns:
        更新后的等级信息
    """
    level = Level.get_by_id(level_id)
    if not level:
        return error_response('等级不存在', 404)

    data = request.get_json()
    if not data:
        return error_response('请求数据不能为空', 400)

    # 更新字段
    if 'name' in data:
        name = data.get('name', '').strip()
        if name and name != level.name:
            if Level.get_by_name(name):
                return error_response('等级名称已存在', 400)
            level.name = name

    if 'description' in data:
        level.description = data.get('description', '').strip()

    if 'order_index' in data:
        level.order_index = data.get('order_index', 0)

    if 'is_active' in data:
        level.is_active = bool(data.get('is_active'))

    try:
        db.session.commit()
        return success_response(data=level.to_dict(), message="等级更新成功")
    except Exception as e:
        db.session.rollback()
        return error_response(f'更新等级失败: {str(e)}', 500)


@admin_bp.route('/api/levels/<int:level_id>', methods=['DELETE'])
@login_required
@admin_required
@api_response
def delete_level(level_id):
    """删除等级API

    Args:
        level_id: 等级ID

    Returns:
        删除成功信息
    """
    level = Level.get_by_id(level_id)
    if not level:
        return error_response('等级不存在', 404)

    try:
        db.session.delete(level)
        db.session.commit()
        return success_response(message="等级删除成功")
    except Exception as e:
        db.session.rollback()
        return error_response(f'删除等级失败: {str(e)}', 500)


# ==================== 试卷管理API ====================

@admin_bp.route('/api/exams', methods=['GET'])
@login_required
@admin_required
@api_response
def get_exams():
    """获取试卷列表API

    Query Parameters:
        page: 页码（可选，默认1）
        per_page: 每页数量（可选，默认20）
        subject_id: 按科目ID过滤（可选）
        level_id: 按等级ID过滤（可选）
        is_temporary: 按试卷类型过滤（可选，true/false）
        search: 搜索关键词（可选）

    Returns:
        试卷列表
    """
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    subject_id = request.args.get('subject_id', None)
    level_id = request.args.get('level_id', None)
    is_temporary = request.args.get('is_temporary', None)
    search = request.args.get('search', '').strip()

    # 构建查询，使用 joinedload 预加载关联对象
    from sqlalchemy.orm import joinedload

    query = Exam.query.options(
        joinedload(Exam.subject),
        joinedload(Exam.level)
    )

    if subject_id:
        query = query.filter_by(subject_id=subject_id)

    if level_id:
        query = query.filter_by(level_id=level_id)

    if is_temporary is not None:
        query = query.filter_by(is_temporary=is_temporary.lower() == 'true')

    if search:
        query = query.filter(Exam.title.ilike(f'%{search}%'))

    # 分页
    pagination = query.order_by(desc(Exam.created_at)).paginate(
        page=page, per_page=per_page, error_out=False
    )

    exams = pagination.items

    return pagination_response(
        items=[exam.to_dict() for exam in exams],
        total=pagination.total,
        page=pagination.page,
        per_page=pagination.per_page,
        message="查询成功"
    )


@admin_bp.route('/api/exams/<int:exam_id>', methods=['GET'])
@login_required
@admin_required
@api_response
def get_exam(exam_id):
    """获取单个试卷详情API

    Args:
        exam_id: 试卷ID

    Returns:
        试卷详情
    """
    exam = Exam.get_by_id(exam_id)
    if not exam:
        return error_response('试卷不存在', 404)

    return success_response(data=exam.to_dict(include_questions=True))


@admin_bp.route('/api/exams', methods=['POST'])
@login_required
@admin_required
@api_response
def create_exam():
    """创建试卷API

    Request JSON:
        title: 试卷标题
        subject_id: 科目ID（可选）
        level_id: 等级ID（可选）
        total_points: 总分（可选，默认100）
        description: 考试描述（可选）
        duration_minutes: 考试时长（分钟）（可选）
        start_time: 开始时间（可选）
        end_time: 结束时间（可选）
        max_attempts: 最大尝试次数（可选，默认1）
        pass_score: 及格分数（可选，默认60.0）
        is_active: 是否激活（可选，默认true）

    Returns:
        创建的试卷信息
    """
    data = request.get_json()
    if not data:
        return error_response('请求数据不能为空', 400)

    # 验证必填字段
    if 'title' not in data:
        return error_response('缺少必填字段: title', 400)

    title = data.get('title', '').strip()
    subject_id = data.get('subject_id')
    level_id = data.get('level_id')
    total_points = data.get('total_points', 100)
    description = data.get('description', '').strip()
    duration_minutes = data.get('duration_minutes')
    start_time = data.get('start_time')
    end_time = data.get('end_time')
    max_attempts = data.get('max_attempts', 1)
    pass_score = data.get('pass_score', 60.0)
    is_active = data.get('is_active', True)

    # 验证输入
    is_valid, error_msg = validate_string(title, '试卷标题', min_length=1, max_length=200, allow_empty=False)
    if not is_valid:
        return error_response(error_msg, 400)

    try:
        from datetime import datetime

        exam = Exam(
            title=title,
            subject_id=subject_id,
            level_id=level_id,
            total_points=total_points,
            description=description,
            duration_minutes=duration_minutes,
            start_time=datetime.fromisoformat(start_time) if start_time else None,
            end_time=datetime.fromisoformat(end_time) if end_time else None,
            max_attempts=max_attempts,
            pass_score=pass_score,
            is_active=is_active
        )
        db.session.add(exam)
        db.session.commit()

        return {
            'exam': exam.to_dict(),
            'message': '试卷创建成功'
        }, 201
    except ValueError as e:
        return error_response(f'时间格式错误: {str(e)}', 400)
    except Exception as e:
        db.session.rollback()
        return error_response(f'创建试卷失败: {str(e)}', 500)


@admin_bp.route('/api/exams/<int:exam_id>', methods=['PUT'])
@login_required
@admin_required
@api_response
def update_exam(exam_id):
    """更新试卷API

    Args:
        exam_id: 试卷ID

    Request JSON:
        title: 试卷标题（可选）
        subject_id: 科目ID（可选）
        level_id: 等级ID（可选）
        total_points: 总分（可选）
        description: 考试描述（可选）
        duration_minutes: 考试时长（可选）
        start_time: 开始时间（可选）
        end_time: 结束时间（可选）
        max_attempts: 最大尝试次数（可选）
        pass_score: 及格分数（可选）
        is_active: 是否激活（可选）

    Returns:
        更新后的试卷信息
    """
    exam = Exam.get_by_id(exam_id)
    if not exam:
        return error_response('试卷不存在', 404)

    data = request.get_json()
    if not data:
        return error_response('请求数据不能为空', 400)

    # 更新字段
    if 'title' in data:
        exam.title = data.get('title', '').strip()

    if 'subject_id' in data:
        exam.subject_id = data.get('subject_id')

    if 'level_id' in data:
        exam.level_id = data.get('level_id')

    if 'total_points' in data:
        exam.total_points = data.get('total_points', 100)

    if 'description' in data:
        exam.description = data.get('description', '').strip()

    if 'duration_minutes' in data:
        exam.duration_minutes = data.get('duration_minutes')

    if 'max_attempts' in data:
        exam.max_attempts = data.get('max_attempts', 1)

    if 'pass_score' in data:
        exam.pass_score = data.get('pass_score', 60.0)

    if 'is_active' in data:
        exam.is_active = bool(data.get('is_active'))

    # 处理时间字段
    if 'start_time' in data:
        try:
            exam.start_time = datetime.fromisoformat(data['start_time']) if data['start_time'] else None
        except ValueError as e:
            return error_response(f'开始时间格式错误: {str(e)}', 400)

    if 'end_time' in data:
        try:
            exam.end_time = datetime.fromisoformat(data['end_time']) if data['end_time'] else None
        except ValueError as e:
            return error_response(f'结束时间格式错误: {str(e)}', 400)

    try:
        db.session.commit()
        return success_response(data=exam.to_dict(), message="试卷更新成功")
    except Exception as e:
        db.session.rollback()
        return error_response(f'更新试卷失败: {str(e)}', 500)


@admin_bp.route('/api/exams/<int:exam_id>', methods=['DELETE'])
@login_required
@admin_required
@api_response
def delete_exam(exam_id):
    """删除试卷API

    Args:
        exam_id: 试卷ID

    Returns:
        删除成功信息
    """
    exam = Exam.get_by_id(exam_id)
    if not exam:
        return error_response('试卷不存在', 404)

    try:
        db.session.delete(exam)
        db.session.commit()
        return success_response(message="试卷删除成功")
    except Exception as e:
        db.session.rollback()
        return error_response(f'删除试卷失败: {str(e)}', 500)


@admin_bp.route('/api/exams/batch-delete', methods=['DELETE'])
@login_required
@admin_required
@api_response
def batch_delete_exams():
    """批量删除试卷API

    Request JSON:
        exam_ids: 试卷ID列表

    Returns:
        删除成功信息
    """
    data = request.get_json()
    if not data:
        return error_response('请求数据不能为空', 400)

    exam_ids = data.get('exam_ids', [])
    if not exam_ids or not isinstance(exam_ids, list):
        return error_response('请提供有效的试卷ID列表', 400)

    # 查询要删除的试卷
    exams = Exam.query.filter(Exam.id.in_(exam_ids)).all()
    if not exams:
        return error_response('未找到要删除的试卷', 404)

    deleted_count = 0
    try:
        for exam in exams:
            db.session.delete(exam)
            deleted_count += 1
        db.session.commit()
        return success_response(
            data={'deleted_count': deleted_count},
            message=f'成功删除 {deleted_count} 个试卷'
        )
    except Exception as e:
        db.session.rollback()
        return error_response(f'批量删除试卷失败: {str(e)}', 500)


# ==================== 题目管理API ====================

@admin_bp.route('/api/questions', methods=['GET'])
@login_required
@admin_required
@api_response
def get_questions():
    """获取题目列表API

    Query Parameters:
        page: 页码（可选，默认1）
        per_page: 每页数量（可选，默认20）
        exam_id: 按试卷ID过滤（可选）
        type: 按题型过滤（可选）
        search: 搜索关键词（可选，搜索题目内容和考点）
        knowledge_point_id: 按分配的知识点ID过滤（可选）
        is_temporary: 按是否为临时题目过滤（可选，true/false）
                      临时题目：关联的试卷is_temporary=true
                      试卷题目：exam_id为空或关联的试卷is_temporary=false

    Returns:
        题目列表
    """
    from sqlalchemy.orm import joinedload

    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    exam_id = request.args.get('exam_id', None)
    question_type = request.args.get('type', None)
    search = request.args.get('search', '').strip()
    knowledge_point_id = request.args.get('knowledge_point_id', None)
    is_temporary = request.args.get('is_temporary', None)

    # 构建查询，使用 joinedload 预加载关联对象
    query = Question.query.options(
        joinedload(Question.exam)
    )

    if exam_id:
        query = query.filter_by(exam_id=exam_id)

    if question_type:
        query = query.filter_by(type=question_type)

    if knowledge_point_id:
        query = query.filter_by(knowledge_point_id=int(knowledge_point_id))

    if is_temporary is not None:
        # 过滤临时题目或试卷题目
        # 临时题目：关联的试卷 is_temporary=true
        # 试卷题目：exam_id为空 或 关联的试卷 is_temporary=false
        if is_temporary.lower() == 'true':
            # 只显示临时题目（关联的试卷是临时试卷）
            from app.models.exam import Exam
            query = query.join(Exam, Question.exam_id == Exam.id).filter(Exam.is_temporary == True)
        else:
            # 只显示非临时题目（exam_id为空 或 关联的试卷不是临时试卷）
            # 使用 OR 条件：exam_id IS NULL OR exam关联的试卷 is_temporary=false
            from sqlalchemy import or_
            from app.models.exam import Exam
            query = query.outerjoin(Exam, Question.exam_id == Exam.id).filter(
                or_(Question.exam_id == None, Exam.is_temporary == False)
            )

    if search:
        # 搜索题目内容
        query = query.filter(Question.content.ilike(f'%{search}%'))

        # 注意：SQLite 不支持直接搜索 JSON 字段
        # 如果需要搜索 metadata 中的考点文本，可以在查询后进行过滤
        # PostgreSQL 可以使用: Question.question_metadata['knowledge_point_text'].astext.ilike(f'%{search}%')

    # 分页
    pagination = query.order_by(Question.order_index).paginate(
        page=page, per_page=per_page, error_out=False
    )

    questions = pagination.items

    return pagination_response(
        items=[question.to_dict(include_exam=True) for question in questions],
        total=pagination.total,
        page=pagination.page,
        per_page=pagination.per_page,
        message="查询成功"
    )


@admin_bp.route('/api/questions/<int:question_id>', methods=['GET'])
@login_required
@admin_required
@api_response
def get_question(question_id):
    """获取单个题目详情API

    Args:
        question_id: 题目ID

    Returns:
        题目详情
    """
    question = Question.get_by_id(question_id)
    if not question:
        return error_response('题目不存在', 404)

    return success_response(data=question.to_dict(include_exam=True))


@admin_bp.route('/api/questions', methods=['POST'])
@login_required
@admin_required
@api_response
def create_question():
    """创建题目API

    Request JSON:
        exam_id: 试卷ID
        type: 题型
        content: 题目内容
        correct_answer: 正确答案
        points: 分值（可选，默认10）
        order_index: 排序索引（可选，默认0）
        options: 选项列表（可选）
        explanation: 答案解析（可选）
        has_image: 是否包含图片（可选，默认false）

    Returns:
        创建的题目信息
    """
    data = request.get_json()
    if not data:
        return error_response('请求数据不能为空', 400)

    # 验证必填字段
    required_fields = ['type', 'content', 'correct_answer']
    for field in required_fields:
        if field not in data:
            return error_response(f'缺少必填字段: {field}', 400)

    exam_id = data.get('exam_id')
    question_type = data.get('type')
    content = data.get('content', '').strip()
    correct_answer = data.get('correct_answer')
    points = data.get('points', data.get('score', 10))  # 兼容 score 和 points
    order_index = data.get('order_index', 0)
    options = data.get('options')
    explanation = data.get('explanation', '').strip()
    has_image = data.get('has_image', False)

    # 验证输入
    is_valid, error_msg = validate_string(content, '题目内容', min_length=1, allow_empty=False)
    if not is_valid:
        return error_response(error_msg, 400)

    try:
        question = Question(
            exam_id=exam_id,
            type=question_type,
            content=content,
            correct_answer=correct_answer,
            points=points,
            order_index=order_index,
            options=options,
            explanation=explanation,
            has_image=has_image
        )
        db.session.add(question)
        db.session.commit()

        return success_response(data=question.to_dict(include_exam=True), message="题目创建成功")
    except Exception as e:
        db.session.rollback()
        return error_response(f'创建题目失败: {str(e)}', 500)


@admin_bp.route('/api/questions/<int:question_id>', methods=['PUT'])
@login_required
@admin_required
@api_response
def update_question(question_id):
    """更新题目API

    Args:
        question_id: 题目ID

    Request JSON:
        type: 题型（可选）
        content: 题目内容（可选）
        correct_answer: 正确答案（可选）
        points: 分值（可选）
        order_index: 排序索引（可选）
        options: 选项列表（可选）
        explanation: 答案解析（可选）

    Returns:
        更新后的题目信息
    """
    question = Question.get_by_id(question_id)
    if not question:
        return error_response('题目不存在', 404)

    data = request.get_json()
    if not data:
        return error_response('请求数据不能为空', 400)

    # 更新字段
    if 'type' in data:
        question.type = data.get('type')

    if 'content' in data:
        question.content = data.get('content', '').strip()

    if 'correct_answer' in data:
        question.correct_answer = data.get('correct_answer')

    if 'points' in data:
        question.points = data.get('points', 10)

    if 'order_index' in data:
        question.order_index = data.get('order_index', 0)

    if 'options' in data:
        question.options = data.get('options')

    if 'explanation' in data:
        question.explanation = data.get('explanation', '').strip()

    if 'has_image' in data:
        question.has_image = bool(data.get('has_image'))

    if 'image_data' in data:
        question.image_data = data.get('image_data')

    if 'knowledge_point_id' in data:
        question.knowledge_point_id = data.get('knowledge_point_id')

    try:
        db.session.commit()
        return success_response(data=question.to_dict(), message="题目更新成功")
    except Exception as e:
        db.session.rollback()
        return error_response(f'更新题目失败: {str(e)}', 500)


@admin_bp.route('/api/questions/<int:question_id>', methods=['DELETE'])
@login_required
@admin_required
@api_response
def delete_question(question_id):
    """删除题目API

    Args:
        question_id: 题目ID

    Returns:
        删除成功信息
    """
    question = Question.get_by_id(question_id)
    if not question:
        return error_response('题目不存在', 404)

    try:
        db.session.delete(question)
        db.session.commit()
        return success_response(message="题目删除成功")
    except Exception as e:
        db.session.rollback()
        return error_response(f'删除题目失败: {str(e)}', 500)


@admin_bp.route('/api/questions/batch-delete', methods=['DELETE'])
@login_required
@admin_required
@api_response
def batch_delete_questions():
    """批量删除题目API

    Request JSON:
        question_ids: 题目ID列表

    Returns:
        删除成功信息
    """
    data = request.get_json()
    if not data:
        return error_response('请求数据不能为空', 400)

    question_ids = data.get('question_ids', [])
    if not question_ids or not isinstance(question_ids, list):
        return error_response('请提供有效的题目ID列表', 400)

    # 查询要删除的题目
    questions = Question.query.filter(Question.id.in_(question_ids)).all()
    if not questions:
        return error_response('未找到要删除的题目', 404)

    deleted_count = 0
    try:
        for question in questions:
            db.session.delete(question)
            deleted_count += 1
        db.session.commit()
        return success_response(
            data={'deleted_count': deleted_count},
            message=f'成功删除 {deleted_count} 个题目'
        )
    except Exception as e:
        db.session.rollback()
        return error_response(f'批量删除题目失败: {str(e)}', 500)


@admin_bp.route('/api/exams/<int:exam_id>/questions', methods=['GET'])
@login_required
@admin_required
@api_response
def get_exam_questions(exam_id):
    """获取试卷题目列表API

    Args:
        exam_id: 试卷ID

    Returns:
        试卷题目列表
    """
    exam = Exam.get_by_id(exam_id)
    if not exam:
        return error_response('试卷不存在', 404)

    # 使用 Exam.get_all_questions() 获取所有题目
    questions = exam.get_all_questions()

    return success_response(data=[question.to_dict() for question in questions])


@admin_bp.route('/api/exams/<int:exam_id>/questions', methods=['POST'])
@login_required
@admin_required
@api_response
def create_exam_question(exam_id):
    """为试卷创建题目API

    Args:
        exam_id: 试卷ID

    Request JSON:
        type: 题型
        content: 题目内容
        answer: 正确答案
        score: 分值
        options: 选项列表（可选）
        explanation: 答案解析（可选）

    Returns:
        创建的题目信息
    """
    exam = Exam.get_by_id(exam_id)
    if not exam:
        return error_response('试卷不存在', 404)

    data = request.get_json()
    if not data:
        return error_response('请求数据不能为空', 400)

    question_type = data.get('type')
    content = data.get('content', '').strip()
    answer = data.get('answer')
    score = data.get('score', 5)
    options = data.get('options')
    explanation = data.get('explanation', '').strip()

    try:
        # 获取当前最大排序索引
        max_order = db.session.query(db.func.max(Question.order_index)).filter_by(exam_id=exam_id).scalar() or 0

        question = Question(
            exam_id=exam_id,
            type=question_type,
            content=content,
            correct_answer=answer,
            points=score,
            order_index=max_order + 1,
            options=options,
            explanation=explanation
        )
        db.session.add(question)
        db.session.commit()

        return {
            'data': question.to_dict(),
            'message': '题目创建成功'
        }, 201
    except Exception as e:
        db.session.rollback()
        return error_response(f'创建题目失败: {str(e)}', 500)


# ==================== 提交管理API ====================

@admin_bp.route('/api/submissions', methods=['GET'])
@login_required
@admin_required
@api_response
def get_submissions():
    """获取提交列表API

    Query Parameters:
        page: 页码（可选，默认1）
        per_page: 每页数量（可选，默认20）
        exam_id: 按试卷ID过滤（可选）
        user_id: 按用户ID过滤（可选）
        status: 按状态过滤（可选）
        search: 搜索关键词（可选）

    Returns:
        提交列表
    """
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    exam_id = request.args.get('exam_id', None)
    user_id = request.args.get('user_id', None)
    status = request.args.get('status', None)
    search = request.args.get('search', '').strip()

    # 构建查询
    query = Submission.query

    if exam_id:
        query = query.filter_by(exam_id=exam_id)

    if user_id:
        query = query.filter_by(user_id=user_id)

    if status:
        query = query.filter_by(status=status)

    if search:
        query = query.filter(
            db.or_(
                Submission.student_name.ilike(f'%{search}%')
            )
        )

    # 分页
    pagination = query.order_by(desc(Submission.submit_time)).paginate(
        page=page, per_page=per_page, error_out=False
    )

    submissions = pagination.items

    return pagination_response(
        items=[submission.to_dict() for submission in submissions],
        total=pagination.total,
        page=pagination.page,
        per_page=pagination.per_page,
        message="查询成功"
    )


@admin_bp.route('/api/submissions/<int:submission_id>', methods=['GET'])
@login_required
@admin_required
@api_response
def get_submission(submission_id):
    """获取单个提交详情API

    Args:
        submission_id: 提交ID

    Returns:
        提交详情
    """
    submission = Submission.get_by_id(submission_id)
    if not submission:
        return error_response('提交不存在', 404)

    return success_response(data=submission.to_dict(include_answers=True))


@admin_bp.route('/api/submissions/<int:submission_id>', methods=['PUT'])
@login_required
@admin_required
@api_response
def update_submission(submission_id):
    """更新提交API

    Args:
        submission_id: 提交ID

    Request JSON:
        status: 状态（可选）
        obtained_score: 实际得分（可选）
        score_percentage: 得分百分比（可选）
        is_passed: 是否及格（可选）

    Returns:
        更新后的提交信息
    """
    submission = Submission.get_by_id(submission_id)
    if not submission:
        return error_response('提交不存在', 404)

    data = request.get_json()
    if not data:
        return error_response('请求数据不能为空', 400)

    # 更新字段
    if 'status' in data:
        submission.status = data.get('status')

    if 'obtained_score' in data:
        submission.obtained_score = data.get('obtained_score')

    if 'score_percentage' in data:
        submission.score_percentage = data.get('score_percentage')

    if 'is_passed' in data:
        submission.is_passed = bool(data.get('is_passed'))

    try:
        db.session.commit()
        return success_response(data=submission.to_dict(), message="提交更新成功")
    except Exception as e:
        db.session.rollback()
        return error_response(f'更新提交失败: {str(e)}', 500)


@admin_bp.route('/api/submissions/<int:submission_id>', methods=['DELETE'])
@login_required
@admin_required
@api_response
def delete_submission(submission_id):
    """删除提交API

    Args:
        submission_id: 提交ID

    Returns:
        删除成功信息
    """
    submission = Submission.get_by_id(submission_id)
    if not submission:
        return error_response('提交不存在', 404)

    try:
        db.session.delete(submission)
        db.session.commit()
        return success_response(message="提交删除成功")
    except Exception as e:
        db.session.rollback()
        return error_response(f'删除提交失败: {str(e)}', 500)


@admin_bp.route('/api/submissions/batch-delete', methods=['DELETE'])
@login_required
@admin_required
@api_response
def batch_delete_submissions():
    """批量删除提交API

    Request JSON:
        submission_ids: 提交ID列表

    Returns:
        删除成功信息
    """
    data = request.get_json()
    if not data:
        return error_response('请求数据不能为空', 400)

    submission_ids = data.get('submission_ids', [])
    if not submission_ids or not isinstance(submission_ids, list):
        return error_response('请提供有效的提交ID列表', 400)

    # 查询要删除的提交
    submissions = Submission.query.filter(Submission.id.in_(submission_ids)).all()
    if not submissions:
        return error_response('未找到要删除的提交', 404)

    deleted_count = 0
    try:
        for submission in submissions:
            db.session.delete(submission)
            deleted_count += 1
        db.session.commit()
        return success_response(
            data={'deleted_count': deleted_count},
            message=f'成功删除 {deleted_count} 个提交'
        )
    except Exception as e:
        db.session.rollback()
        return error_response(f'批量删除提交失败: {str(e)}', 500)


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

    return success_response(data=stats, message="统计信息获取成功")


@admin_bp.route('/api/upload-image', methods=['POST'])
@login_required
@admin_required
def upload_image():
    """上传图片接口

    Request:
        file: 图片文件
        type: 图片类型（question_image, option_image等）

    Returns:
        图片路径信息
    """
    if 'file' not in request.files:
        return error_response('没有上传文件', 400)

    file = request.files['file']
    if file.filename == '':
        return error_response('没有选择文件', 400)

    # 检查文件类型
    allowed_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}
    ext = Path(file.filename).suffix.lower()
    if ext not in allowed_extensions:
        return error_response('不支持的文件类型', 400)

    # 检查文件大小（最大5MB）
    file.seek(0, os.SEEK_END)
    file_size = file.tell()
    file.seek(0)
    max_size = 5 * 1024 * 1024  # 5MB
    if file_size > max_size:
        return error_response('文件大小超过限制（最大5MB）', 400)

    # 生成唯一文件名
    unique_id = uuid.uuid4().hex[:8]
    filename = f"image_{unique_id}{ext}"

    # 保存到uploads/images目录
    upload_dir = Path(current_app.config.get('UPLOAD_FOLDER', 'uploads')) / 'images'
    upload_dir.mkdir(parents=True, exist_ok=True)
    file_path = upload_dir / filename

    try:
        file.save(str(file_path))

        # 返回相对于uploads目录的路径
        relative_path = f"images/{filename}"

        return success_response(
            data={
                'path': relative_path,
                'filename': filename,
                'size': file_size
            },
            message="图片上传成功"
        )
    except Exception as e:
        return error_response(f'图片保存失败: {str(e)}', 500)