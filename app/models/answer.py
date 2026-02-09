"""答题记录模型"""

import json
from typing import Dict, Optional, Any
from datetime import datetime
from app.extensions import db
from .base import BaseModel


class Answer(BaseModel):
    """
    答题记录模型
    
    表示对单个题目的答题记录
    """
    
    __tablename__ = 'answers'
    
    # 字段定义
    submission_id = db.Column(
        db.Integer,
        db.ForeignKey('submissions.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
        doc='提交记录ID'
    )
    question_id = db.Column(
        db.Integer,
        db.ForeignKey('questions.id'),
        nullable=False,
        index=True,
        doc='题目ID'
    )
    student_answer = db.Column(
        db.Text,
        nullable=True,
        doc='学生答案'
    )
    score = db.Column(
        db.Numeric(5, 2),
        default=0.0,
        nullable=False,
        doc='本题得分'
    )
    is_correct = db.Column(
        db.Boolean,
        default=False,
        nullable=False,
        index=True,
        doc='是否正确'
    )
    grading_details = db.Column(
        db.JSON,
        nullable=True,
        doc='判卷详情，如判卷规则、匹配程度等'
    )
    answered_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        nullable=False,
        doc='答题时间'
    )
    
    # 关系定义
    submission = db.relationship(
        'Submission',
        back_populates='answers',
        lazy='joined',
        doc='关联的提交记录'
    )
    question = db.relationship(
        'Question',
        back_populates='answers',
        lazy='joined',
        doc='关联的题目'
    )
    
    def __init__(
        self,
        submission_id: int,
        question_id: int,
        student_answer: Optional[str] = None,
        score: float = 0.0,
        is_correct: bool = False,
        grading_details: Optional[Dict[str, Any]] = None
    ):
        """
        初始化答题记录
        
        Args:
            submission_id: 提交记录ID
            question_id: 题目ID
            student_answer: 学生答案（可选）
            score: 得分，默认0.0
            is_correct: 是否正确，默认False
            grading_details: 判卷详情（可选）
        """
        self.submission_id = submission_id
        self.question_id = question_id
        self.student_answer = student_answer
        self.score = score
        self.is_correct = is_correct
        self.grading_details = grading_details or {}
        self.answered_at = datetime.utcnow()
    
    @classmethod
    def get_by_submission_and_question(
        cls,
        submission_id: int,
        question_id: int
    ) -> Optional['Answer']:
        """
        根据提交记录和题目获取答题记录
        
        Args:
            submission_id: 提交记录ID
            question_id: 题目ID
            
        Returns:
            答题记录实例，如果不存在则返回None
        """
        return cls.query.filter_by(
            submission_id=submission_id,
            question_id=question_id
        ).first()
    
    def get_question_text(self) -> str:
        """
        获取题目文本
        
        Returns:
            题目文本
        """
        return self.question.text if self.question else ''
    
    def get_correct_answer(self) -> str:
        """
        获取正确答案
        
        Returns:
            正确答案
        """
        return self.question.correct_answer if self.question else ''
    
    def get_points(self) -> int:
        """
        获取题目分值
        
        Returns:
            题目分值
        """
        return self.question.points if self.question else 0
    
    def get_question_type(self) -> str:
        """
        获取题目类型
        
        Returns:
            题目类型
        """
        return self.question.type if self.question else ''
    
    def get_options(self) -> list:
        """
        获取题目选项
        
        Returns:
            选项列表
        """
        if self.question and self.question.options:
            if isinstance(self.question.options, str):
                try:
                    return json.loads(self.question.options)
                except json.JSONDecodeError:
                    return []
            return self.question.options
        return []
    
    def update_grading_result(
        self,
        score: float,
        is_correct: bool,
        grading_details: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        更新判卷结果
        
        Args:
            score: 得分
            is_correct: 是否正确
            grading_details: 判卷详情（可选）
        """
        self.score = score
        self.is_correct = is_correct
        if grading_details:
            self.grading_details = grading_details
        
        # 更新提交记录的总分
        if self.submission:
            self.submission.calculate_score()
        
        db.session.commit()
    
    def to_dict(self, include_question: bool = False) -> dict:
        """
        转换为字典，可包含关联的题目信息
        
        Args:
            include_question: 是否包含题目信息
            
        Returns:
            包含答题记录信息的字典
        """
        data = super().to_dict()
        
        # 处理JSON字段
        if 'grading_details' in data and data['grading_details']:
            if isinstance(data['grading_details'], str):
                try:
                    data['grading_details'] = json.loads(data['grading_details'])
                except json.JSONDecodeError:
                    data['grading_details'] = {}
        
        # 添加关联信息
        if include_question and self.question:
            data['question_text'] = self.get_question_text()
            data['correct_answer'] = self.get_correct_answer()
            data['question_type'] = self.get_question_type()
            data['question_points'] = self.get_points()
            data['question_options'] = self.get_options()
        
        if self.submission:
            data['student_name'] = self.submission.student_name
        
        return data
    
    def __repr__(self) -> str:
        """友好的字符串表示"""
        return f'<Answer id={self.id} submission_id={self.submission_id} question_id={self.question_id}>'