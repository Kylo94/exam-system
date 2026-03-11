"""add exam questions table

Revision ID: add_exam_questions_table
Revises: 5f43d8aa9fe7
Create Date: 2026-03-04 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_exam_questions_table'
down_revision = '5f43d8aa9fe7'
branch_labels = None
depends_on = None


def upgrade():
    # 创建考试-题目关联表
    op.create_table(
        'exam_questions',
        sa.Column('exam_id', sa.Integer(), nullable=False),
        sa.Column('question_id', sa.Integer(), nullable=False),
        sa.Column('order_index', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('points', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['exam_id'], ['exams.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['question_id'], ['questions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('exam_id', 'question_id')
    )
    op.create_index(op.f('ix_exam_questions_exam_id'), 'exam_questions', ['exam_id'], unique=False)
    op.create_index(op.f('ix_exam_questions_question_id'), 'exam_questions', ['question_id'], unique=False)


def downgrade():
    op.drop_index(op.f('ix_exam_questions_question_id'), table_name='exam_questions')
    op.drop_index(op.f('ix_exam_questions_exam_id'), table_name='exam_questions')
    op.drop_table('exam_questions')
