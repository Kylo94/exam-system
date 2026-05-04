"""
应用配置 - FastAPI版本

注意：AI配置（API Key等）请在系统管理页面 /admin/ai-configs 中配置
这些配置存储在数据库中，支持多账号管理
"""
import os
from typing import Set
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用配置"""

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore"  # 忽略未定义的字段
    )

    # 应用配置
    APP_NAME: str = "在线答题系统"
    DEBUG: bool = True
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # 日志配置
    LOG_LEVEL: str = "DEBUG"  # DEBUG, INFO, WARNING, ERROR, CRITICAL
    LOG_DIR: str = "logs"
    LOG_MAX_BYTES: int = 10 * 1024 * 1024  # 10MB
    LOG_BACKUP_COUNT: int = 5

    # 密钥配置
    SECRET_KEY: str = "dev-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24小时

    # 数据库配置
    DATABASE_URL: str = f"sqlite://{os.path.abspath('./data/exam_system.db')}"
    DB_ECHO: bool = False
    GENERATE_SCHEMA: bool = True  # 开发环境开启，生产环境应关闭

    # 管理员配置
    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD: str = "admin"
    ADMIN_EMAIL: str = "admin@example.com"

    # 文件上传配置
    MAX_CONTENT_LENGTH: int = 16 * 1024 * 1024  # 16MB
    UPLOAD_FOLDER: str = "uploads"

    # CORS配置
    ALLOWED_ORIGINS: Set[str] = {"*"}


def get_settings() -> Settings:
    """获取配置"""
    return Settings()


settings = get_settings()
