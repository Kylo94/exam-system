"""
AI配置模型 - Tortoise-ORM
"""
from tortoise import fields
from tortoise.models import Model


class AIConfig(Model):
    """AI配置模型"""

    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=100)
    provider = fields.CharField(max_length=50)  # deepseek, openai, minimax
    model = fields.CharField(max_length=100)
    api_key = fields.CharField(max_length=500, null=True)
    base_url = fields.CharField(max_length=255, null=True)
    temperature = fields.FloatField(default=0.7)
    max_tokens = fields.IntField(default=2000)
    is_active = fields.BooleanField(default=False)
    is_default = fields.BooleanField(default=False)
    description = fields.TextField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    # 关系
    creator = fields.ForeignKeyField(
        "models.User",
        related_name="ai_configs",
        on_delete=fields.CASCADE,
    )

    class Meta:
        table = "ai_configs"

    def __str__(self):
        return f"<AIConfig {self.name}>"
