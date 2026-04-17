"""
知识点模型 - Tortoise-ORM
"""
from tortoise import fields
from tortoise.models import Model


class KnowledgePoint(Model):
    """知识点模型"""

    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=200)
    subject = fields.ForeignKeyField(
        "models.Subject",
        related_name="knowledge_points",
        on_delete=fields.CASCADE,
    )
    level = fields.ForeignKeyField(
        "models.Level",
        related_name="knowledge_points",
        null=True,
        on_delete=fields.SET_NULL,
    )
    description = fields.TextField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    # 关系
    questions: fields.ReverseRelation["Question"]

    class Meta:
        table = "knowledge_points"
        unique_together = (("name", "subject"),)

    def __str__(self):
        return f"<KnowledgePoint {self.name}>"
