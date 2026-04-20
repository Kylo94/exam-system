"""
系统设置模型
"""
from tortoise import fields
from tortoise.models import Model


class SystemSettings(Model):
    """系统设置模型"""

    id = fields.IntField(pk=True)
    key = fields.CharField(max_length=100, unique=True, description="设置键名")
    value = fields.TextField(null=True, description="设置值")
    value_type = fields.CharField(max_length=20, default="string", description="值类型: string, int, bool, json")
    description = fields.CharField(max_length=500, null=True, description="设置描述")
    category = fields.CharField(max_length=50, default="general", description="设置分类")
    is_public = fields.BooleanField(default=False, description="是否公开显示")
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "system_settings"

    def __str__(self):
        return f"<SystemSettings {self.key}={self.value}>"

    @classmethod
    async def get_value(cls, key: str, default=None):
        """获取设置值"""
        setting = await cls.get_or_none(key=key)
        if not setting:
            return default
        return cls._convert_value(setting.value, setting.value_type)

    @classmethod
    async def set_value(cls, key: str, value, value_type="string", description=None, category="general", is_public=False):
        """设置值"""
        setting = await cls.get_or_none(key=key)
        if setting:
            setting.value = str(value) if value_type == "string" else value
            setting.value_type = value_type
            if description:
                setting.description = description
            await setting.save()
        else:
            await cls.create(
                key=key,
                value=str(value) if value_type == "string" else value,
                value_type=value_type,
                description=description,
                category=category,
                is_public=is_public
            )

    @staticmethod
    def _convert_value(value, value_type):
        """转换值类型"""
        if value_type == "int":
            try:
                return int(value)
            except (ValueError, TypeError):
                return 0
        elif value_type == "bool":
            return value in ("true", "True", "1", "yes", True)
        elif value_type == "json":
            import json
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                return None
        return value

    @classmethod
    async def get_all_settings(cls, category: str = None):
        """获取所有设置"""
        query = cls.all()
        if category:
            query = query.filter(category=category)
        settings = await query
        result = {}
        for s in settings:
            result[s.key] = cls._convert_value(s.value, s.value_type)
        return result

    @classmethod
    async def initialize_defaults(cls):
        """初始化默认设置"""
        defaults = [
            {"key": "app_name", "value": "在线答题系统", "value_type": "string", "description": "系统名称", "category": "general"},
            {"key": "app_version", "value": "4.0", "value_type": "string", "description": "系统版本", "category": "general", "is_public": True},
            {"key": "allow_register", "value": "true", "value_type": "bool", "description": "允许新用户注册", "category": "security"},
            {"key": "require_email_verification", "value": "false", "value_type": "bool", "description": "注册需邮箱验证", "category": "security"},
            {"key": "exam_default_duration", "value": "60", "value_type": "int", "description": "默认考试时长(分钟)", "category": "exam"},
            {"key": "exam_default_total_points", "value": "100", "value_type": "int", "description": "默认试卷总分", "category": "exam"},
            {"key": "exam_default_pass_score", "value": "60", "value_type": "int", "description": "默认及格分数", "category": "exam"},
            {"key": "submission_max_per_day", "value": "10", "value_type": "int", "description": "每人每天最大提交次数", "category": "exam"},
            {"key": "ai_enabled", "value": "true", "value_type": "bool", "description": "启用AI功能", "category": "ai"},
            {"key": "auto_grade_essay", "value": "false", "value_type": "bool", "description": "AI自动批改简答题", "category": "ai"},
        ]
        for d in defaults:
            exists = await cls.get_or_none(key=d["key"])
            if not exists:
                await cls.create(**d)
