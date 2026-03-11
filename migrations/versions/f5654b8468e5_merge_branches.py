"""merge branches

Revision ID: f5654b8468e5
Revises: add_exam_questions_table, add_teacher_bind_requests_table
Create Date: 2026-03-04 17:40:25.876765

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f5654b8468e5'
down_revision = ('add_exam_questions_table', 'add_teacher_bind_requests_table')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
