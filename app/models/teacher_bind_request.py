"""
教师绑定申请模型 - Tortoise-ORM
"""
from tortoise import fields
from tortoise.models import Model


class TeacherBindRequest(Model):
    """教师绑定申请模型"""

    id = fields.IntField(pk=True)
    student = fields.ForeignKeyField(
        "models.User",
        related_name="bind_requests",
        on_delete=fields.CASCADE,
    )
    teacher = fields.ForeignKeyField(
        "models.User",
        related_name="student_requests",
        on_delete=fields.CASCADE,
    )
    status = fields.CharField(max_length=20, default="pending")  # pending, approved, rejected
    message = fields.TextField(null=True)
    admin_note = fields.TextField(null=True)
    processed_at = fields.DatetimeField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "teacher_bind_requests"
        ordering = ["-created_at"]

    def __str__(self):
        return f"<TeacherBindRequest {self.id}: {self.student_id} -> {self.teacher_id}>"
