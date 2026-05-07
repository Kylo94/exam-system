"""
学生试卷访问授权模型
"""
from tortoise import fields
from tortoise.models import Model


class StudentExamAccess(Model):
    """学生试卷访问授权 - 教师给学生授权可访问的试卷类型"""

    id = fields.IntField(pk=True)
    student = fields.ForeignKeyField("models.User", related_name="exam_accesses")
    teacher = fields.ForeignKeyField("models.User", related_name="granted_accesses")
    subject = fields.ForeignKeyField("models.Subject", related_name="student_accesses")
    level = fields.ForeignKeyField("models.Level", null=True, related_name="student_accesses")
    granted_at = fields.DatetimeField(auto_now_add=True)
    granted_by = fields.ForeignKeyField("models.User", related_name="given_accesses")

    class Meta:
        table = "student_exam_accesses"
        indexes = [("student", "subject", "level")]

    def __str__(self):
        level_str = self.level.name if self.level else "所有等级"
        return f"{self.student.username} - {self.subject.name} - {level_str}"