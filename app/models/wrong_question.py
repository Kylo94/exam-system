"""
错题记录模型
"""
from tortoise import fields
from tortoise.models import Model


class WrongQuestion(Model):
    """错题记录 - 记录学生的错题"""

    id = fields.IntField(pk=True)
    student = fields.ForeignKeyField("models.User", related_name="wrong_questions")
    question = fields.ForeignKeyField("models.Question", related_name="wrong_records")
    submission = fields.ForeignKeyField("models.Submission", related_name="wrong_questions")
    student_answer = fields.TextField(description="学生答案")
    correct_answer = fields.TextField(description="正确答案")
    is_wrong = fields.BooleanField(default=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "wrong_questions"
        indexes = [("student", "question"), ("created_at",)]

    def __str__(self):
        return f"{self.student.username} - 错题 #{self.question_id}"
