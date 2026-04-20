"""
试卷模型 - Tortoise-ORM
"""
from tortoise import fields
from tortoise.models import Model
from datetime import datetime

from app.services.id_generator import format_display_id


class Exam(Model):
    """试卷模型"""

    id = fields.IntField(pk=True)
    title = fields.CharField(max_length=200)
    subject = fields.ForeignKeyField(
        "models.Subject",
        related_name="exams",
        on_delete=fields.CASCADE,
    )
    level = fields.ForeignKeyField(
        "models.Level",
        related_name="exams",
        null=True,
        on_delete=fields.SET_NULL,
    )
    creator = fields.ForeignKeyField(
        "models.User",
        related_name="exams_created",
        on_delete=fields.CASCADE,
    )
    total_points = fields.IntField(default=100)
    is_temporary = fields.BooleanField(default=False)
    is_published = fields.BooleanField(default=False)
    duration_minutes = fields.IntField(default=60)
    pass_score = fields.IntField(default=60)
    description = fields.TextField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    # 关系
    questions: fields.ManyToManyRelation["Question"]
    submissions: fields.ReverseRelation["Submission"]

    class Meta:
        table = "exams"
        ordering = ["-created_at"]

    @property
    def display_id(self) -> str:
        """获取显示用的ID"""
        return format_display_id(self.id, "exam")

    def __str__(self):
        return f"<Exam {self.title}>"

    @property
    def question_count(self) -> int:
        """题目数量"""
        return self.questions.count() if hasattr(self, "questions") else 0
