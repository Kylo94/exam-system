"""add subject_id to levels table

Revision ID: add_subject_id_to_levels
Revises: 03efd9b53b39
Create Date: 2026-02-25

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision = 'add_subject_id_to_levels'
down_revision = '03efd9b53b39'
branch_labels = None
depends_on = None


def upgrade():
    """添加subject_id外键到levels表"""

    # 检查是否已经有科目数据
    conn = op.get_bind()
    result = conn.execute(text("SELECT COUNT(*) FROM subjects")).scalar()

    if result == 0 or result is None:
        # 如果没有科目，创建一个默认科目
        conn.execute(text("""
            INSERT INTO subjects (name, description, is_active, order_index, created_at, updated_at)
            VALUES ('默认科目', '系统自动创建的默认科目', 1, 0, datetime('now'), datetime('now'))
        """))
        conn.commit()

    # 添加subject_id列（先允许NULL）
    op.add_column('levels', sa.Column('subject_id', sa.Integer(), nullable=True))

    # 为所有现有等级分配科目ID
    conn.execute(text("""
        UPDATE levels
        SET subject_id = (SELECT MIN(id) FROM subjects)
        WHERE subject_id IS NULL
    """))
    conn.commit()

    # 现在将subject_id设置为NOT NULL
    # SQLite不支持直接修改列为NOT NULL，需要重建表
    # 使用批量迁移策略

    # 创建新表
    op.execute("""
        CREATE TABLE levels_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subject_id INTEGER NOT NULL,
            name VARCHAR(50) NOT NULL,
            description TEXT,
            is_active BOOLEAN NOT NULL DEFAULT 1,
            order_index INTEGER NOT NULL DEFAULT 0,
            created_at DATETIME,
            updated_at DATETIME,
            FOREIGN KEY (subject_id) REFERENCES subjects (id) ON DELETE CASCADE
        )
    """)

    # 复制数据
    op.execute("""
        INSERT INTO levels_new (id, subject_id, name, description, is_active, order_index, created_at, updated_at)
        SELECT id, subject_id, name, description, is_active, order_index, created_at, updated_at
        FROM levels
    """)

    # 删除旧表
    op.execute("DROP TABLE levels")

    # 重命名新表
    op.execute("ALTER TABLE levels_new RENAME TO levels")

    # 重新创建索引
    op.execute("CREATE INDEX ix_levels_name ON levels (name)")
    op.execute("CREATE INDEX ix_levels_subject_id ON levels (subject_id)")


def downgrade():
    """移除subject_id外键，恢复旧结构"""

    # 创建旧表结构
    op.execute("""
        CREATE TABLE levels_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name VARCHAR(50) NOT NULL UNIQUE,
            description TEXT,
            is_active BOOLEAN NOT NULL DEFAULT 1,
            order_index INTEGER NOT NULL DEFAULT 0,
            created_at DATETIME,
            updated_at DATETIME
        )
    """)

    # 复制数据（去掉subject_id）
    op.execute("""
        INSERT INTO levels_new (id, name, description, is_active, order_index, created_at, updated_at)
        SELECT id, name, description, is_active, order_index, created_at, updated_at
        FROM levels
    """)

    # 删除新表
    op.execute("DROP TABLE levels")

    # 重命名
    op.execute("ALTER TABLE levels_new RENAME TO levels")

    # 重新创建索引
    op.execute("CREATE INDEX ix_levels_name ON levels (name)")

