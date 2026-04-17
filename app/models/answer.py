"""
答案记录模型 - Tortoise-ORM
"""
from tortoise import fields
from tortoise.models import Model


class Answer(Model):
    """答案记录模型"""

    id = fields.IntField(pk=True)
    submission = fields.ForeignKeyField(
        "models.Submission",
        related_name="answers",
        on_delete=fields.CASCADE,
    )
    question = fields.ForeignKeyField(
        "models.Question",
        related_name="answers",
        on_delete=fields.CASCADE,
    )
    user_answer = fields.TextField()
    is_correct = fields.BooleanField(null=True)
    score = fields.IntField(null=True)
    ai_graded = fields.BooleanField(default=False)
    ai_feedback = fields.TextField(null=True)
    graded_at = fields.DatetimeField(null=True)
    order_num = fields.IntField(default=0)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "answers"
        ordering = ["order_num", "id"]

    def __str__(self):
        return f"<Answer {self.id} for Question {self.question_id}>"

    async def grade(self) -> bool:
        """自动评分"""
        if self.question.type in ["single_choice", "multiple_choice", "true_false"]:
            self.is_correct = self.question.check_answer(self.user_answer)
            self.score = self.question.points if self.is_correct else 0
        else:
            # 其他题型需要AI批改
            self.ai_graded = False
        await self.save()
        return self.is_correct or False
