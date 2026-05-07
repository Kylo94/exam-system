"""
Tortoise-ORM 数据模型
"""
from app.models.ai_config import AIConfig
from app.models.answer import Answer
from app.models.audit_log import AuditLog
from app.models.exam import Exam
from app.models.knowledge_point import KnowledgePoint
from app.models.level import Level
from app.models.question import Question
from app.models.student_exam_access import StudentExamAccess
from app.models.subject import Subject
from app.models.submission import Submission
from app.models.system_settings import SystemSettings
from app.models.teacher_bind_request import TeacherBindRequest
from app.models.user import User
from app.models.wrong_question import WrongQuestion

__all__ = [
    "User",
    "Subject",
    "Level",
    "KnowledgePoint",
    "Exam",
    "Question",
    "Submission",
    "Answer",
    "AIConfig",
    "TeacherBindRequest",
    "SystemSettings",
    "AuditLog",
    "StudentExamAccess",
    "WrongQuestion",
]
