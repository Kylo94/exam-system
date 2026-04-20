"""
科目模型 - Tortoise-ORM
"""
from tortoise import fields
from tortoise.models import Model

from app.services.id_generator import format_display_id


class Subject(Model):
    """科目模型"""

    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=100, unique=True)
    description = fields.TextField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    # 关系
    exams: fields.ReverseRelation["Exam"]
    knowledge_points: fields.ReverseRelation["KnowledgePoint"]

    class Meta:
        table = "subjects"

    @property
    def display_id(self) -> str:
        """获取显示用的ID"""
        return format_display_id(self.id, "subject")

    def __str__(self):
        return f"<Subject {self.name}>"
