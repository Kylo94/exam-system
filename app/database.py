"""
数据库配置 - Tortoise-ORM
"""
from tortoise import Tortoise


async def init_db():
    """初始化数据库"""
    await Tortoise.init(
        db_url=settings.DATABASE_URL,
        modules={"models": ["app.models"]},
    )
    await Tortoise.generate_schemas()


async def close_db():
    """关闭数据库连接"""
    await Tortoise.close_connections()


from app.config import settings
