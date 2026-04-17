#!/usr/bin/env python3
"""
在线答题系统 - FastAPI版本启动脚本
"""
import os
import sys
import subprocess
from pathlib import Path

# 确保项目根目录在Python路径中
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


def create_admin():
    """创建初始管理员账户"""
    import asyncio
    from tortoise import Tortoise
    from app.models.user import User
    from app.config import settings

    async def _create_admin():
        await Tortoise.init(
            db_url="sqlite://./exam_system.db",
            modules={"models": ["app.models"]},
        )
        await Tortoise.generate_schemas()

        # 检查管理员是否存在
        admin = await User.get_or_none(username=settings.ADMIN_USERNAME)
        if not admin:
            admin = User(
                username=settings.ADMIN_USERNAME,
                email=settings.ADMIN_EMAIL,
                role="admin",
                is_active=True,
            )
            admin.set_password(settings.ADMIN_PASSWORD)
            await admin.save()
            print(f"✅ 管理员账户已创建: {settings.ADMIN_USERNAME}")
        else:
            print(f"ℹ️  管理员账户已存在: {settings.ADMIN_USERNAME}")

        await Tortoise.close_connections()

    asyncio.run(_create_admin())


def init_database():
    """初始化数据库"""
    import asyncio
    from tortoise import Tortoise

    async def _init():
        await Tortoise.init(
            db_url="sqlite://./exam_system.db",
            modules={"models": ["app.models"]},
        )
        await Tortoise.generate_schemas()
        await Tortoise.close_connections()
        print("✅ 数据库初始化完成")

    asyncio.run(_init())


def run_server(reload: bool = False):
    """运行开发服务器"""
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=reload,
        log_level="info",
    )


def run_docker():
    """使用Docker运行"""
    print("🚀 启动Docker容器...")
    subprocess.run(["docker-compose", "up", "-d", "--build"], check=True)
    print("✅ 应用已启动，访问 http://localhost:8000")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="在线答题系统 - FastAPI版本")
    parser.add_argument(
        "command",
        nargs="?",
        default="server",
        choices=["server", "init-db", "create-admin", "docker"],
        help="命令：server(默认), init-db, create-admin, docker",
    )
    parser.add_argument("--reload", action="store_true", help="启用热重载")
    parser.add_argument("--init", action="store_true", help="初始化数据库后启动")

    args = parser.parse_args()

    if args.command == "init-db":
        init_database()
    elif args.command == "create-admin":
        create_admin()
    elif args.command == "docker":
        run_docker()
    else:  # server
        if args.init or args.create_admin:
            create_admin()
        run_server(reload=args.reload)


if __name__ == "__main__":
    main()
