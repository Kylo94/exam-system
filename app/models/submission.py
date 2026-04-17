"""
答题提交模型 - Tortoise-ORM
"""
from tortoise import fields
from tortoise.models import Model
from datetime import datetime


class Submission(Model):
    """答题提交记录模型"""

    id = fields.IntField(pk=True)
    exam = fields.ForeignKeyField(
        "models.Exam",
        related_name="submissions",
        on_delete=fields.CASCADE,
    )
    user = fields.ForeignKeyField(
        "models.User",
        related_name="submissions",
        on_delete=fields.CASCADE,
    )
    status = fields.CharField(
        max_length=20,
        default="in_progress"
    )  # in_progress, submitted, grading, graded
    obtained_score = fields.IntField(null=True)
    total_score = fields.IntField(default=100)
    is_passed = fields.BooleanField(null=True)
    started_at = fields.DatetimeField(null=True)
    submitted_at = fields.DatetimeField(null=True)
    graded_at = fields.DatetimeField(null=True)
    duration_seconds = fields.IntField(null=True)
    ip_address = fields.CharField(max_length=50, null=True)
    user_agent = fields.TextField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    # 关系
    answers: fields.ReverseRelation["Answer"]

    class Meta:
        table = "submissions"
        ordering = ["-created_at"]

    def __str__(self):
        return f"<Submission {self.id} by {self.user_id}>"

    @property
    def score_percentage(self) -> float:
        """得分百分比"""
        if self.total_score and self.total_score > 0:
            return (self.obtained_score or 0) / self.total_score * 100
        return 0

    async def calculate_score(self) -> int:
        """计算得分"""
        total = 0
        answers = await self.answers.all()
        for answer in answers:
            if answer.is_correct:
                total += answer.question.points if answer.question else 0
        self.obtained_score = total
        await self.save()
        return total

    async def check_passed(self) -> bool:
        """检查是否及格"""
        if self.obtained_score is not None:
            self.is_passed = self.obtained_score >= self.exam.pass_score
            await self.save()
        return self.is_passed or False
