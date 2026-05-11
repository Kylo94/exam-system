"""Tag驱动知识点关联 - 数据库迁移

为 Question 添加 tags 字段(JSON数组)
为 KnowledgePoint 添加 tags 字段(JSON数组)

由于 SQLite 不支持 JSON 类型，tags 在数据库中存为 JSON 字符串
Tortoise ORM 会自动处理 Python list 与 JSON 字符串之间的转换
"""
import sqlite3
import json
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "exam_system.db"


def migrate():
    """执行迁移"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 1. 为 questions 表添加 tags 字段
    cursor.execute("PRAGMA table_info(questions)")
    columns = [col[1] for col in cursor.fetchall()]
    if 'tags' not in columns:
        cursor.execute("ALTER TABLE questions ADD COLUMN tags TEXT DEFAULT '[]'")
        print("[迁移] questions 表已添加 tags 字段")
    else:
        print("[跳过] questions.tags 字段已存在")

    # 2. 为 knowledge_points 表添加 tags 字段
    cursor.execute("PRAGMA table_info(knowledge_points)")
    columns = [col[1] for col in cursor.fetchall()]
    if 'tags' not in columns:
        cursor.execute("ALTER TABLE knowledge_points ADD COLUMN tags TEXT DEFAULT '[]'")
        print("[迁移] knowledge_points 表已添加 tags 字段")
    else:
        print("[跳过] knowledge_points.tags 字段已存在")

    conn.commit()
    conn.close()
    print("[完成] 数据库迁移完成")


if __name__ == "__main__":
    migrate()
