"""
题目模型 - Tortoise-ORM
"""
from tortoise import fields
from tortoise.models import Model
import json


class Question(Model):
    """题目模型"""

    id = fields.IntField(pk=True)
    exam = fields.ForeignKeyField(
        "models.Exam",
        related_name="questions",
        on_delete=fields.CASCADE,
        null=True,
    )
    type = fields.CharField(max_length=20)  # single_choice, multiple_choice, true_false, fill_blank, essay, coding
    content = fields.TextField()
    options = fields.JSONField(default={})  # 存储选项 {"A": "...", "B": "...", ...}
    correct_answer = fields.TextField()  # 正确答案
    points = fields.IntField(default=10)
    explanation = fields.TextField(null=True)
    knowledge_point = fields.ForeignKeyField(
        "models.KnowledgePoint",
        related_name="questions",
        null=True,
        on_delete=fields.SET_NULL,
    )
    difficulty = fields.IntField(default=1)  # 1-5难度
    order_num = fields.IntField(default=0)  # 题目顺序
    images = fields.JSONField(default=list)  # 题目内容中的多张图片路径列表 ["path1", "path2"]
    question_metadata = fields.JSONField(default=dict)  # 题目元数据，包含选项图片等信息

    @property
    def has_image(self) -> bool:
        """题目是否包含图片"""
        return bool(self.images)

    @property
    def image_data(self) -> str:
        """兼容旧接口，返回第一张图片"""
        return self.images[0] if self.images else None
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    # 关系
    answers: fields.ReverseRelation["Answer"]

    class Meta:
        table = "questions"
        ordering = ["order_num", "id"]

    def __str__(self):
        return f"<Question {self.id}: {self.content[:50]}>"

    @property
    def type_display(self) -> str:
        """题型显示名称"""
        type_map = {
            "single_choice": "单选题",
            "multiple_choice": "多选题",
            "true_false": "判断题",
            "fill_blank": "填空题",
            "essay": "简答题",
            "coding": "编程题",
        }
        return type_map.get(self.type, self.type)

    def get_options_list(self) -> list:
        """获取选项列表"""
        if isinstance(self.options, dict):
            return [{"key": k, "value": v} for k, v in self.options.items()]
        return []

    def check_answer(self, user_answer: str) -> bool:
        """检查答案是否正确"""
        if self.type in ["single_choice", "multiple_choice", "true_false"]:
            return user_answer.strip().upper() == self.correct_answer.strip().upper()
        # 其他题型需要AI批改
        return False
