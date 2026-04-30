"""管理员路由子模块"""
from .index import router as index_router
from .users import router as users_router
from .subjects import router as subjects_router
from .exams import router as exams_router
from .questions import router as questions_router
from .misc import router as misc_router

__all__ = ["index_router", "users_router", "subjects_router", "exams_router", "questions_router", "misc_router"]