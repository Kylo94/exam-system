"""用户认证路由模块

提供用户注册、登录、注销、个人信息管理等功能。
"""

from flask import Blueprint, request, render_template, redirect, url_for
from flask_login import login_user, logout_user, login_required, current_user

from app.extensions import db
from app.models.user import User
from app.utils.validators import (
    validate_string, validate_email, validate_password, validate_choice, batch_validate
)
from app.utils.response_utils import (
    error_response, validation_error_response, api_response
)

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')


# ==================== 页面路由 ====================

@auth_bp.route('/login', methods=['GET'])
def login_page():
    """登录页面"""
    if current_user.is_authenticated:
        if current_user.is_student():
            return redirect(url_for('main.index'))
        else:
            return redirect(url_for('main.dashboard'))
    return render_template('auth/login.html')


@auth_bp.route('/register', methods=['GET'])
def register_page():
    """注册页面"""
    if current_user.is_authenticated:
        if current_user.is_student():
            return redirect(url_for('main.index'))
        else:
            return redirect(url_for('main.dashboard'))
    return render_template('auth/register.html')


@auth_bp.route('/profile', methods=['GET'])
@login_required
def profile_page():
    """个人资料页面"""
    return render_template('auth/profile.html', user=current_user)


@auth_bp.route('/forgot-password', methods=['GET'])
def forgot_password_page():
    """忘记密码页面"""
    if current_user.is_authenticated:
        if current_user.is_student():
            return redirect(url_for('main.index'))
        else:
            return redirect(url_for('main.dashboard'))
    return render_template('auth/forgot_password.html')


@auth_bp.route('/reset-password/<token>', methods=['GET'])
def reset_password_page(token):
    """重置密码页面"""
    if current_user.is_authenticated:
        if current_user.is_student():
            return redirect(url_for('main.index'))
        else:
            return redirect(url_for('main.dashboard'))
    return render_template('auth/reset_password.html', token=token)


# ==================== API路由 ====================

@auth_bp.route('/api/login', methods=['POST'])
@api_response
def login():
    """用户登录API
    
    Request JSON:
        username: 用户名或邮箱
        password: 密码
        remember: 是否记住登录（可选）
    
    Returns:
        登录成功信息或错误信息
    """
    data = request.get_json()
    if not data:
        return error_response('请求数据不能为空', 400)
    
    # 验证必填字段
    required_fields = ['username', 'password']
    for field in required_fields:
        if field not in data:
            return error_response(f'缺少必填字段: {field}', 400)
    
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()
    remember = data.get('remember', False)
    
    # 验证输入
    is_valid, error_msg = validate_string(username, '用户名', min_length=1, allow_empty=False)
    if not is_valid:
        return error_response(error_msg, 400)
    
    is_valid, error_msg = validate_string(password, '密码', min_length=1, allow_empty=False)
    if not is_valid:
        return error_response(error_msg, 400)
    
    # 用户认证
    user = User.authenticate(username, password)
    if not user:
        return error_response('用户名或密码错误', 401)
    
    # 登录用户
    login_user(user, remember=remember)
    user.update_last_login()
    
    return {
        'user': user.to_dict(),
        'message': '登录成功'
    }, 200


@auth_bp.route('/api/register', methods=['POST'])
@api_response
def register():
    """用户注册API
    
    Request JSON:
        username: 用户名
        email: 邮箱地址
        password: 密码
        confirm_password: 确认密码
        role: 用户角色（可选，默认student）
    
    Returns:
        注册成功信息或错误信息
    """
    data = request.get_json()
    if not data:
        return error_response('请求数据不能为空', 400)
    
    # 验证必填字段
    required_fields = ['username', 'email', 'password', 'confirm_password']
    for field in required_fields:
        if field not in data:
            return error_response(f'缺少必填字段: {field}', 400)
    
    username = data.get('username', '').strip()
    email = data.get('email', '').strip().lower()
    password = data.get('password', '').strip()
    confirm_password = data.get('confirm_password', '').strip()
    role = data.get('role', 'student').strip()
    teacher_id = data.get('teacher_id')
    
    # 批量验证
    validators = {
        'username': (validate_string, {'field_name': '用户名', 'min_length': 3, 'max_length': 20, 'allow_empty': False}),
        'email': (validate_email, {'field_name': '邮箱地址', 'allow_none': False}),
        'password': (validate_password, {'field_name': '密码', 'allow_none': False}),
        'role': (validate_choice, {'field_name': '用户角色', 'choices': ['teacher', 'student'], 'allow_none': True}),
    }
    
    errors = batch_validate(validators, {
        'username': username,
        'email': email,
        'password': password,
        'role': role,
    })
    
    # 自定义验证：密码确认
    if password != confirm_password:
        if 'password' not in errors:
            errors['password'] = []
        errors['password'].append('两次输入的密码不一致')
    
    if errors:
        return validation_error_response(errors)
    
    # 检查用户名和邮箱是否已存在
    if User.get_by_username(username):
        return error_response('用户名已存在', 409)
    
    if User.get_by_email(email):
        return error_response('邮箱地址已存在', 409)
    
    # 验证教师ID（仅学生角色）
    validated_teacher_id = None
    if role == 'student' and teacher_id:
        teacher = User.get_by_id(teacher_id)
        if not teacher:
            return error_response('教师ID不存在', 400)
        if not teacher.is_teacher():
            return error_response('指定的用户不是教师', 400)
        validated_teacher_id = teacher_id
    
    # 创建用户
    try:
        user = User(
            username=username,
            email=email,
            password=password,
            role=role,
            teacher_id=validated_teacher_id
        )
        db.session.add(user)
        db.session.commit()
        
        # 自动登录
        login_user(user, remember=False)
        
        return {
            'user': user.to_dict(),
            'message': '注册成功'
        }, 201
        
    except Exception as e:
        db.session.rollback()
        return error_response(f'注册失败: {str(e)}', 500)


@auth_bp.route('/api/logout', methods=['POST'])
@login_required
@api_response
def logout():
    """用户注销API
    
    Returns:
        注销成功信息
    """
    logout_user()
    return {'message': '注销成功'}, 200


@auth_bp.route('/api/profile', methods=['GET'])
@login_required
@api_response
def get_profile():
    """获取当前用户信息API
    
    Returns:
        用户信息
    """
    return current_user.to_dict(include_sensitive=True), 200


@auth_bp.route('/api/profile', methods=['PUT'])
@login_required
@api_response
def update_profile():
    """更新用户信息API
    
    Request JSON:
        username: 新用户名（可选）
        email: 新邮箱地址（可选）
        profile: 用户配置文件（可选）
    
    Returns:
        更新后的用户信息
    """
    data = request.get_json()
    if not data:
        return error_response('请求数据不能为空', 400)
    
    user = current_user
    updates = {}
    
    # 更新用户名
    if 'username' in data:
        new_username = data['username'].strip()
        is_valid, error_msg = validate_string(
            new_username, '用户名', min_length=3, max_length=20, allow_empty=False
        )
        if not is_valid:
            return error_response(error_msg, 400)
        
        # 检查用户名是否已存在（排除当前用户）
        existing_user = User.get_by_username(new_username)
        if existing_user and existing_user.id != user.id:
            return error_response('用户名已存在', 409)
        
        updates['username'] = new_username
    
    # 更新邮箱
    if 'email' in data:
        new_email = data['email'].strip().lower()
        is_valid, error_msg = validate_email(new_email, '邮箱地址', allow_none=False)
        if not is_valid:
            return error_response(error_msg, 400)
        
        # 检查邮箱是否已存在（排除当前用户）
        existing_user = User.get_by_email(new_email)
        if existing_user and existing_user.id != user.id:
            return error_response('邮箱地址已存在', 409)
        
        updates['email'] = new_email
    
    # 更新配置文件
    if 'profile' in data:
        updates['profile'] = data['profile']
    
    # 应用更新
    if updates:
        try:
            for key, value in updates.items():
                setattr(user, key, value)
            
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            return error_response(f'更新失败: {str(e)}', 500)
    
    return user.to_dict(include_sensitive=True), 200


@auth_bp.route('/api/change-password', methods=['POST'])
@login_required
@api_response
def change_password():
    """修改密码API
    
    Request JSON:
        current_password: 当前密码
        new_password: 新密码
        confirm_password: 确认新密码
    
    Returns:
        修改成功信息
    """
    data = request.get_json()
    if not data:
        return error_response('请求数据不能为空', 400)
    
    required_fields = ['current_password', 'new_password', 'confirm_password']
    for field in required_fields:
        if field not in data:
            return error_response(f'缺少必填字段: {field}', 400)
    
    current_password = data.get('current_password', '').strip()
    new_password = data.get('new_password', '').strip()
    confirm_password = data.get('confirm_password', '').strip()
    
    # 验证当前密码
    if not current_user.check_password(current_password):
        return error_response('当前密码错误', 401)
    
    # 验证新密码
    is_valid, error_msg = validate_password(new_password, '新密码', allow_none=False)
    if not is_valid:
        return error_response(error_msg, 400)
    
    # 验证密码确认
    if new_password != confirm_password:
        return error_response('两次输入的新密码不一致', 400)
    
    # 验证新旧密码不能相同
    if current_password == new_password:
        return error_response('新密码不能与当前密码相同', 400)
    
    # 更新密码
    try:
        current_user.set_password(new_password)
        db.session.commit()
        return {'message': '密码修改成功'}, 200
    except Exception as e:
        db.session.rollback()
        return error_response(f'密码修改失败: {str(e)}', 500)


@auth_bp.route('/api/check-username/<username>', methods=['GET'])
@api_response
def check_username(username):
    """检查用户名是否可用
    
    Args:
        username: 要检查的用户名
    
    Returns:
        用户名可用性信息
    """
    is_valid, error_msg = validate_string(
        username, '用户名', min_length=3, max_length=20, allow_empty=False
    )
    if not is_valid:
        return error_response(error_msg, 400)
    
    existing_user = User.get_by_username(username)
    return {
        'available': not existing_user,
        'username': username
    }, 200


@auth_bp.route('/api/check-email/<email>', methods=['GET'])
@api_response
def check_email(email):
    """检查邮箱是否可用
    
    Args:
        email: 要检查的邮箱地址
    
    Returns:
        邮箱可用性信息
    """
    is_valid, error_msg = validate_email(email, '邮箱地址', allow_none=False)
    if not is_valid:
        return error_response(error_msg, 400)
    
    existing_user = User.get_by_email(email)
    return {
        'available': not existing_user,
        'email': email
    }, 200


@auth_bp.route('/api/verify-teacher/<int:teacher_id>', methods=['GET'])
@api_response
def verify_teacher(teacher_id):
    """验证教师ID是否有效
    
    Args:
        teacher_id: 教师ID
    
    Returns:
        教师验证信息
    """
    teacher = User.get_by_id(teacher_id)
    
    if not teacher:
        return error_response('教师ID不存在', 404)
    
    if not teacher.is_teacher():
        return error_response('该用户不是教师', 400)
    
    return {
        'valid': True,
        'teacher_id': teacher_id,
        'teacher_name': teacher.username
    }, 200


@auth_bp.route('/api/bind-teacher', methods=['POST'])
@login_required
@api_response
def bind_teacher():
    """绑定教师
    
    Request JSON:
        teacher_id: 教师ID
    
    Returns:
        绑定结果
    """
    if not current_user.is_student():
        return error_response('只有学生可以绑定教师', 403)
    
    data = request.get_json()
    if not data or 'teacher_id' not in data:
        return error_response('缺少教师ID', 400)
    
    teacher_id = data.get('teacher_id')
    
    # 验证教师
    teacher = User.get_by_id(teacher_id)
    if not teacher:
        return error_response('教师ID不存在', 404)
    
    if not teacher.is_teacher():
        return error_response('指定的用户不是教师', 400)
    
    # 绑定教师
    try:
        if current_user.bind_teacher(teacher_id):
            return {
                'message': f'成功绑定教师：{teacher.username}',
                'teacher_id': teacher_id,
                'teacher_name': teacher.username
            }, 200
        else:
            return error_response('绑定教师失败', 500)
    except Exception as e:
        return error_response(f'绑定教师失败: {str(e)}', 500)


# ==================== 辅助函数 ====================

def init_auth(app):
    """初始化认证系统
    
    Args:
        app: Flask应用实例
    """
    # 设置登录视图
    from app.extensions import login_manager
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login_page'
    login_manager.login_message = '请先登录'
    login_manager.login_message_category = 'warning'
    
    # 注册蓝图
    app.register_blueprint(auth_bp)


# 导出蓝图
__all__ = ['auth_bp', 'init_auth']