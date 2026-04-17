"""
Tortoise-ORM 数据模型
"""
from app.models.user import User
from app.models.subject import Subject
from app.models.level import Level
from app.models.knowledge_point import KnowledgePoint
from app.models.exam import Exam
from app.models.question import Question
from app.models.submission import Submission
from app.models.answer import Answer
from app.models.ai_config import AIConfig
from app.models.teacher_bind_request import TeacherBindRequest

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
]
