"""add teacher bind requests table

Revision ID: add_teacher_bind_requests_table
Revises: f3eed5b46a1a
Create Date: 2026-03-04 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_teacher_bind_requests_table'
down_revision = 'f3eed5b46a1a'
branch_labels = None
depends_on = None


def upgrade():
    # 创建teacher_bind_requests表
    op.create_table(
        'teacher_bind_requests',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('student_id', sa.Integer(), nullable=False),
        sa.Column('teacher_id', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='pending'),
        sa.Column('message', sa.Text(), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(), nullable=True),
        sa.Column('reviewed_by', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['student_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['teacher_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['reviewed_by'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # 创建索引
    op.create_index('ix_teacher_bind_requests_student_id', 'teacher_bind_requests', ['student_id'], unique=False)
    op.create_index('ix_teacher_bind_requests_teacher_id', 'teacher_bind_requests', ['teacher_id'], unique=False)


def downgrade():
    # 删除teacher_bind_requests表
    op.drop_index('ix_teacher_bind_requests_teacher_id', table_name='teacher_bind_requests')
    op.drop_index('ix_teacher_bind_requests_student_id', table_name='teacher_bind_requests')
    op.drop_table('teacher_bind_requests')
