"""
知识点模型 - Tortoise-ORM
"""
from tortoise import fields
from tortoise.models import Model

from app.services.id_generator import format_display_id


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
    # 标签，用于匹配题目的文字标签（JSON数组）
    tags = fields.JSONField(default=list, description="标签列表，定义该知识点覆盖哪些标签")
    # 关键词（保留用于兼容，可逐步迁移到 tags）
    keywords = fields.TextField(null=True, description="关键词，逗号分隔")
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    # 关系
    questions: fields.ReverseRelation["Question"]

    class Meta:
        table = "knowledge_points"
        unique_together = (("name", "subject"),)

    @property
    def display_id(self) -> str:
        """获取显示用的ID"""
        return format_display_id(self.id, "knowledge_point")

    def __str__(self):
        return f"<KnowledgePoint {self.name}>"
