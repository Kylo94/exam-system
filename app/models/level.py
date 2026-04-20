"""
难度等级模型 - Tortoise-ORM
"""
from tortoise import fields
from tortoise.models import Model

from app.services.id_generator import format_display_id


class Level(Model):
    """难度等级模型"""

    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=50)
    description = fields.TextField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    # 关联科目
    subject = fields.ForeignKeyField(
        "models.Subject",
        related_name="levels",
        on_delete=fields.CASCADE,
    )

    # 关系
    exams: fields.ReverseRelation["Exam"]
    knowledge_points: fields.ReverseRelation["KnowledgePoint"]

    class Meta:
        table = "levels"

    @property
    def display_id(self) -> str:
        """获取显示用的ID"""
        return format_display_id(self.id, "level")

    def __str__(self):
        return f"<Level {self.name}>"
