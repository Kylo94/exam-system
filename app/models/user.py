"""用户模型"""

import bcrypt
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from flask_login import UserMixin

from app.extensions import db, login_manager
from .base import BaseModel


class User(BaseModel, UserMixin):
    """
    用户模型
    
    属性:
        username: 用户名，唯一
        email: 邮箱地址，唯一
        password_hash: 密码哈希值
        role: 用户角色（admin/teacher/student）
        is_active: 账户是否激活
        last_login_at: 最后登录时间
        profile: 用户配置文件（JSON格式）
    """
    
    __tablename__ = 'users'
    
    username = db.Column(
        db.String(50),
        unique=True,
        nullable=False,
        index=True,
        doc='用户名'
    )
    
    email = db.Column(
        db.String(100),
        unique=True,
        nullable=False,
        index=True,
        doc='邮箱地址'
    )
    
    password_hash = db.Column(
        db.String(128),
        nullable=False,
        doc='密码哈希值'
    )
    
    role = db.Column(
        db.String(20),
        nullable=False,
        default='student',
        doc='用户角色（admin/teacher/student）'
    )
    
    is_active = db.Column(
        db.Boolean,
        nullable=False,
        default=True,
        doc='账户是否激活'
    )
    
    last_login_at = db.Column(
        db.DateTime,
        nullable=True,
        doc='最后登录时间'
    )
    
    profile = db.Column(
        db.JSON,
        nullable=True,
        doc='用户配置文件（JSON格式）'
    )
    
    teacher_id = db.Column(
        db.Integer,
        db.ForeignKey('users.id'),
        nullable=True,
        doc='关联的教师ID（仅学生角色使用）'
    )
    
    # 关系
    submissions = db.relationship(
        'Submission',
        backref='user',
        lazy='dynamic',
        cascade='all, delete-orphan'
    )
    
    # 学生-教师关系
    teacher = db.relationship(
        'User',
        remote_side='User.id',
        backref='students',
        doc='关联的教师'
    )
    
    def __init__(
        self,
        username: str,
        email: str,
        password: str,
        role: str = 'student',
        is_active: bool = True,
        profile: Optional[Dict[str, Any]] = None,
        teacher_id: Optional[int] = None
    ):
        """
        初始化用户
        
        Args:
            username: 用户名
            email: 邮箱地址
            password: 明文密码
            role: 用户角色
            is_active: 是否激活
            profile: 用户配置文件
            teacher_id: 关联的教师ID
        """
        super().__init__()
        self.username = username
        self.email = email
        self.set_password(password)
        self.role = role
        self.is_active = is_active
        self.profile = profile or {}
        self.teacher_id = teacher_id
    
    def set_password(self, password: str) -> None:
        """
        设置密码（生成哈希）
        
        Args:
            password: 明文密码
        """
        if not password:
            raise ValueError("密码不能为空")
        
        # 生成密码哈希
        salt = bcrypt.gensalt()
        self.password_hash = bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
    
    def check_password(self, password: str) -> bool:
        """
        验证密码
        
        Args:
            password: 明文密码
            
        Returns:
            密码是否正确
        """
        if not self.password_hash:
            return False
        
        try:
            return bcrypt.checkpw(
                password.encode('utf-8'),
                self.password_hash.encode('utf-8')
            )
        except (ValueError, TypeError):
            return False
    
    def update_last_login(self) -> None:
        """更新最后登录时间"""
        self.last_login_at = datetime.now(timezone.utc)
        db.session.commit()
    
    def activate(self) -> None:
        """激活账户"""
        self.is_active = True
        db.session.commit()
    
    def deactivate(self) -> None:
        """停用账户"""
        self.is_active = False
        db.session.commit()
    
    def is_admin(self) -> bool:
        """判断是否为管理员"""
        return self.role == 'admin'
    
    def is_teacher(self) -> bool:
        """判断是否为教师"""
        return self.role == 'teacher'
    
    def is_student(self) -> bool:
        """判断是否为学生"""
        return self.role == 'student'
    
    def get_teacher(self) -> Optional['User']:
        """获取学生的教师"""
        if self.is_student():
            return self.teacher
        return None
    
    def get_students(self):
        """获取教师的学生列表"""
        if self.is_teacher():
            return self.students
        return []
    
    def bind_teacher(self, teacher_id: int) -> bool:
        """
        绑定教师
        
        Args:
            teacher_id: 教师ID
            
        Returns:
            是否绑定成功
        """
        if not self.is_student():
            return False
        
        teacher = User.get_by_id(teacher_id)
        if not teacher or not teacher.is_teacher():
            return False
        
        self.teacher_id = teacher_id
        db.session.commit()
        return True
    
    def to_dict(self, include_sensitive: bool = False) -> Dict[str, Any]:
        """
        转换为字典
        
        Args:
            include_sensitive: 是否包含敏感信息（如邮箱）
            
        Returns:
            用户信息字典
        """
        data = super().to_dict()
        
        # 移除敏感字段
        if not include_sensitive:
            data.pop('password_hash', None)
            data.pop('email', None)
        
        # 添加计算属性
        data['is_admin'] = self.is_admin()
        data['is_teacher'] = self.is_teacher()
        data['is_student'] = self.is_student()
        data['teacher_id'] = self.teacher_id
        
        # 添加教师信息（如果是学生）
        if self.is_student() and self.teacher:
            data['teacher'] = {
                'id': self.teacher.id,
                'username': self.teacher.username
            }
        
        return data
    
    def get_id(self):
        """获取用户ID（Flask-Login要求）"""
        return str(self.id)
    
    @property
    def display_name(self) -> str:
        """显示名称（优先使用用户名）"""
        return self.username
    
    @classmethod
    def get_by_username(cls, username: str) -> Optional['User']:
        """
        根据用户名获取用户
        
        Args:
            username: 用户名
            
        Returns:
            用户实例或None
        """
        return cls.query.filter_by(username=username).first()
    
    @classmethod
    def get_by_email(cls, email: str) -> Optional['User']:
        """
        根据邮箱获取用户
        
        Args:
            email: 邮箱地址
            
        Returns:
            用户实例或None
        """
        return cls.query.filter_by(email=email).first()
    
    @classmethod
    def authenticate(cls, username_or_email: str, password: str) -> Optional['User']:
        """
        用户认证
        
        Args:
            username_or_email: 用户名或邮箱
            password: 密码
            
        Returns:
            认证成功的用户实例，失败返回None
        """
        # 尝试通过用户名查找
        user = cls.get_by_username(username_or_email)
        
        # 如果用户名没找到，尝试邮箱
        if not user:
            user = cls.get_by_email(username_or_email)
        
        # 验证用户
        if user and user.check_password(password) and user.is_active:
            return user
        
        return None
    
    def __repr__(self) -> str:
        return f'<User {self.username} ({self.role})>'


@login_manager.user_loader
def load_user(user_id: str):
    """
    加载用户（Flask-Login回调函数）
    
    Args:
        user_id: 用户ID字符串
        
    Returns:
        用户实例或None
    """
    try:
        return User.get_by_id(int(user_id))
    except (ValueError, TypeError):
        return None