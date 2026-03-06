"""考试-题目关联表模型

用于支持多对多关系，特别是临时试卷需要引用题库中的题目
"""

from app.extensions import db


class ExamQuestion(db.Model):
    """
    考试-题目关联表

    支持一个题目被多个试卷引用，一个试卷包含多个题目
    特别适用于临时试卷引用题库题目，而不需要复制题目数据
    """

    __tablename__ = 'exam_questions'

    exam_id = db.Column(
        db.Integer,
        db.ForeignKey('exams.id', ondelete='CASCADE'),
        primary_key=True,
        index=True,
        doc='考试ID'
    )

    question_id = db.Column(
        db.Integer,
        db.ForeignKey('questions.id', ondelete='CASCADE'),
        primary_key=True,
        index=True,
        doc='题目ID'
    )

    order_index = db.Column(
        db.Integer,
        default=0,
        nullable=False,
        doc='题目在试卷中的顺序'
    )

    points = db.Column(
        db.Integer,
        nullable=True,
        doc='本题分值（可覆盖原题目的分值）'
    )

    # 关系定义
    exam = db.relationship(
        'Exam',
        back_populates='exam_questions',
        doc='关联的考试'
    )

    question = db.relationship(
        'Question',
        backref=db.backref('exam_questions', cascade='all, delete-orphan'),
        doc='关联的题目'
    )

    def __repr__(self) -> str:
        """友好的字符串表示"""
        return f'<ExamQuestion exam_id={self.exam_id} question_id={self.question_id}>'
