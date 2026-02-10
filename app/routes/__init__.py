"""Flask路由模块"""

from .main import main_bp
from .subjects import subjects_bp
from .levels import levels_bp
from .exams import exams_bp
from .questions import questions_bp
from .submissions import submissions_bp
from .answers import answers_bp
from .upload import upload_bp
from .auth import auth_bp
from .admin import admin_bp

__all__ = [
    'main_bp',
    'subjects_bp',
    'levels_bp',
    'exams_bp',
    'questions_bp',
    'submissions_bp',
    'answers_bp',
    'upload_bp',
    'auth_bp',
    'admin_bp',
]