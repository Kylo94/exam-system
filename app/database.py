"""
数据库配置 - Tortoise-ORM
"""
import logging
from tortoise import Tortoise

logger = logging.getLogger("database")


async def init_db():
    """初始化数据库"""
    logger.info(f"Starting DB init with URL: {settings.DATABASE_URL}")
    await Tortoise.init(
        db_url=settings.DATABASE_URL,
        modules={"models": ["app.models"]},
        _enable_global_fallback=True,
    )
    logger.info("Tortoise.init completed")
    if settings.GENERATE_SCHEMA:
        await Tortoise.generate_schemas()
        logger.info("Schema generated")
    logger.info("Database initialization complete")


async def close_db():
    """关闭数据库连接"""
    await Tortoise.close_connections()


from app.config import settings
