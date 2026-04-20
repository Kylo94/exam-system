"""
初始化种子数据
运行方式: python scripts/seed_data.py
"""
import asyncio
import sys
sys.path.insert(0, ".")

from tortoise import Tortoise
from app.models.user import User
from app.models.subject import Subject
from app.models.level import Level
from app.models.knowledge_point import KnowledgePoint
from app.models.exam import Exam
from app.auth import get_password_hash


async def seed():
    await Tortoise.init(db_url="sqlite://./data/exam_system.db", modules={"models": ["app.models"]})
    await Tortoise.generate_schemas()

    # 创建管理员
    if not await User.get_or_none(username="admin"):
        await User.create(
            username="admin",
            email="admin@example.com",
            password_hash=get_password_hash("admin123"),
            role="admin"
        )
        print("创建管理员: admin / admin123")

    # 创建教师
    if not await User.get_or_none(username="teacher1"):
        teacher = await User.create(
            username="teacher1",
            email="teacher1@example.com",
            password_hash=get_password_hash("teacher123"),
            role="teacher"
        )
        print("创建教师: teacher1 / teacher123")

    # 创建学生
    if not await User.get_or_none(username="student1"):
        student = await User.create(
            username="student1",
            email="student1@example.com",
            password_hash=get_password_hash("student123"),
            role="student"
        )
        print("创建学生: student1 / student123")

    # 创建更多学生
    for i in range(2, 6):
        if not await User.get_or_none(username=f"student{i}"):
            await User.create(
                username=f"student{i}",
                email=f"student{i}@example.com",
                password_hash=get_password_hash("student123"),
                role="student"
            )
            print(f"创建学生: student{i}")

    # 创建科目及对应的难度等级
    subjects_data = [
        {"name": "数学", "description": "数学科目", "level_count": 3},
        {"name": "语文", "description": "语文科目", "level_count": 3},
        {"name": "英语", "description": "英语科目", "level_count": 3},
        {"name": "物理", "description": "物理科目", "level_count": 3},
        {"name": "化学", "description": "化学科目", "level_count": 3},
    ]

    teacher = await User.get_or_none(username="teacher1")

    for s in subjects_data:
        subject, created = await Subject.get_or_create(
            name=s["name"],
            defaults={"description": s["description"]}
        )
        if created:
            print(f"创建科目: {s['name']}")
            # 为每个科目创建难度等级
            for i in range(1, s["level_count"] + 1):
                level_name = f"第{i}级"
                await Level.create(name=level_name, description=f"{level_name}难度", subject=subject)
                print(f"  创建等级: {level_name}")

    # 获取创建的科目和等级用于创建试卷
    math_subject = await Subject.get_or_none(name="数学")
    if math_subject:
        math_levels = await Level.filter(subject=math_subject)
        level_2 = next((l for l in math_levels if l.name == "第2级"), math_levels[0] if math_levels else None)

        if teacher and level_2:
            exam, created = await Exam.get_or_create(
                title="数学期中考试",
                defaults={
                    "subject": math_subject,
                    "level": level_2,
                    "creator": teacher,
                    "total_points": 100,
                    "is_published": True
                }
            )
            if created:
                print("创建试卷: 数学期中考试")

    # 创建知识点
    kp_data = [
        {"name": "代数基础", "subject_name": "数学", "level_name": "第1级"},
        {"name": "几何", "subject_name": "数学", "level_name": "第2级"},
        {"name": "函数", "subject_name": "数学", "level_name": "第3级"},
        {"name": "阅读理解", "subject_name": "语文", "level_name": "第2级"},
        {"name": "作文", "subject_name": "语文", "level_name": "第2级"},
        {"name": "词汇", "subject_name": "英语", "level_name": "第1级"},
        {"name": "力学", "subject_name": "物理", "level_name": "第2级"},
    ]

    for kp in kp_data:
        subject = await Subject.get_or_none(name=kp["subject_name"])
        if subject:
            level = await Level.filter(subject=subject, name=kp["level_name"]).first()
            kp_obj, created = await KnowledgePoint.get_or_create(
                name=kp["name"],
                subject=subject,
                defaults={"level": level}
            )
            if created:
                print(f"创建知识点: {kp['name']}")

    print("\n种子数据初始化完成!")
    await Tortoise.close_connections()


if __name__ == "__main__":
    asyncio.run(seed())
