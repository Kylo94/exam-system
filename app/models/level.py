"""
难度等级模型 - Tortoise-ORM
"""
from tortoise import fields
from tortoise.models import Model


class Level(Model):
    """难度等级模型"""

    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=50, unique=True)
    description = fields.TextField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    # 关系
    exams: fields.ReverseRelation["Exam"]
    knowledge_points: fields.ReverseRelation["KnowledgePoint"]

    class Meta:
        table = "levels"

    def __str__(self):
        return f"<Level {self.name}>"
