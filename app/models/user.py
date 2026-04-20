"""
用户模型 - Tortoise-ORM
"""
from tortoise import fields
from tortoise.models import Model
from passlib.context import CryptContext

from app.services.id_generator import format_display_id

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class User(Model):
    """用户模型"""

    id = fields.IntField(pk=True)
    username = fields.CharField(max_length=80, unique=True)
    email = fields.CharField(max_length=120, unique=True)
    password_hash = fields.CharField(max_length=255)
    role = fields.CharField(max_length=20, default="student")  # admin, teacher, student
    is_active = fields.BooleanField(default=True)
    profile = fields.JSONField(default={})
    last_login_at = fields.DatetimeField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    # 关系 - 只保留外键关系，不要重复的ID字段
    teacher = fields.ForeignKeyField(
        "models.User",
        related_name="students",
        null=True,
        on_delete=fields.SET_NULL,
    )
    submissions: fields.ReverseRelation["Submission"]
    exams_created: fields.ReverseRelation["Exam"]

    class Meta:
        table = "users"

    @property
    def display_id(self) -> str:
        """获取显示用的ID"""
        return format_display_id(self.id, self.role)

    def verify_password(self, password: str) -> bool:
        """验证密码"""
        return pwd_context.verify(password, self.password_hash)

    def set_password(self, password: str):
        """设置密码"""
        self.password_hash = pwd_context.hash(password)

    @classmethod
    def hash_password(cls, password: str) -> str:
        """密码哈希"""
        return pwd_context.hash(password)

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"

    @property
    def is_teacher(self) -> bool:
        return self.role == "teacher"

    @property
    def is_student(self) -> bool:
        return self.role == "student"

    def __str__(self):
        return f"<User {self.username}>"
