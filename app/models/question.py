"""题目模型"""

import json
from typing import Dict, List, Optional, Any
from app.extensions import db
from .base import BaseModel


class Question(BaseModel):
    """
    题目模型
    
    表示试卷中的一个题目，支持多种题型
    """
    
    __tablename__ = 'questions'
    
    # 字段定义
    exam_id = db.Column(
        db.Integer,
        db.ForeignKey('exams.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
        doc='试卷ID'
    )
    type = db.Column(
        db.String(20),
        nullable=False,
        index=True,
        doc='题型（single_choice/multiple_choice/judgment/fill_blank/subjective/programming）'
    )
    content = db.Column(
        db.Text,
        nullable=False,
        doc='题目内容'
    )
    options = db.Column(
        db.JSON,
        nullable=True,
        doc='选项列表，JSON格式：[{"id": "A", "text": "选项内容"}, ...]'
    )
    correct_answer = db.Column(
        db.Text,
        nullable=False,
        doc='正确答案'
    )
    points = db.Column(
        db.Integer,
        default=10,
        nullable=False,
        doc='分值'
    )
    order_index = db.Column(
        db.Integer,
        default=0,
        nullable=False,
        doc='排序序号'
    )
    has_image = db.Column(
        db.Boolean,
        default=False,
        nullable=False,
        doc='是否包含图片'
    )
    image_data = db.Column(
        db.Text,
        nullable=True,
        doc='图片数据（base64编码或文件路径）'
    )
    explanation = db.Column(
        db.Text,
        nullable=True,
        doc='答案解析'
    )
    question_metadata = db.Column(
        db.JSON,
        nullable=True,
        doc='额外元数据，如解析来源、难度标签等'
    )
    
    # 关系定义
    exam = db.relationship(
        'Exam',
        back_populates='questions',
        lazy='joined',
        doc='关联的试卷'
    )
    answers = db.relationship(
        'Answer',
        back_populates='question',
        lazy='dynamic',
        cascade='all, delete-orphan',
        doc='关联的答题记录'
    )
    
    def __init__(
        self,
        exam_id: int,
        type: str,
        content: str,
        correct_answer: str,
        points: int = 10,
        order_index: int = 0,
        options: Optional[List[Dict[str, Any]]] = None,
        has_image: bool = False,
        image_data: Optional[str] = None,
        explanation: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        初始化题目

        Args:
            exam_id: 试卷ID
            type: 题型
            content: 题目内容
            correct_answer: 正确答案
            points: 分值，默认10
            order_index: 排序序号，默认0
            options: 选项列表（可选）
            has_image: 是否包含图片，默认False
            image_data: 图片数据（可选）
            explanation: 答案解析（可选）
            metadata: 额外元数据（可选）
        """
        self.exam_id = exam_id
        self.type = type
        self.content = content
        self.correct_answer = correct_answer
        self.points = points
        self.order_index = order_index
        self.options = options or []
        self.has_image = has_image
        self.image_data = image_data
        self.explanation = explanation
        self.question_metadata = metadata or {}
    
    @classmethod
    def get_by_exam(cls, exam_id: int) -> List['Question']:
        """
        根据试卷ID获取所有题目

        Args:
            exam_id: 试卷ID

        Returns:
            题目列表，按顺序排序
        """
        return cls.query.filter_by(exam_id=exam_id).order_by(cls.order_index).all()
    
    @classmethod
    def get_types_by_exam(cls, exam_id: int) -> Dict[str, int]:
        """
        获取试卷中各种题型的数量统计
        
        Args:
            exam_id: 试卷ID
            
        Returns:
            题型统计字典，如 {'single_choice': 10, 'judgment': 5}
        """
        from sqlalchemy import func
        result = (
            db.session.query(cls.type, func.count(cls.id))
            .filter_by(exam_id=exam_id)
            .group_by(cls.type)
            .all()
        )
        return dict(result)
    
    def get_options_list(self) -> List[Dict[str, Any]]:
        """
        获取选项列表
        
        Returns:
            选项字典列表，如果options为None则返回空列表
        """
        if self.options is None:
            return []
        
        # 确保返回的是列表
        if isinstance(self.options, str):
            try:
                return json.loads(self.options)
            except json.JSONDecodeError:
                return []
        
        return self.options or []
    
    def get_option_text(self, option_id: str) -> Optional[str]:
        """
        根据选项ID获取选项文本
        
        Args:
            option_id: 选项ID（如'A', 'B'）
            
        Returns:
            选项文本，如果不存在则返回None
        """
        options = self.get_options_list()
        for option in options:
            if option.get('id') == option_id:
                return option.get('text')
        return None
    
    def is_correct_answer(self, student_answer: str) -> bool:
        """
        判断学生答案是否正确
        
        Args:
            student_answer: 学生答案
            
        Returns:
            是否正确
        """
        # 这里可以实现更复杂的判卷逻辑
        # 目前简单字符串比较，后续可在grading_service中扩展
        return str(student_answer).strip() == str(self.correct_answer).strip()
    
    def get_correct_rate(self) -> Optional[float]:
        """
        获取正确率
        
        Returns:
            正确率（0-1），如果没有答题记录则返回None
        """
        answers = self.answers.all()
        if not answers:
            return None
        
        correct_count = sum(1 for answer in answers if answer.is_correct)
        return correct_count / len(answers)
    
    def to_dict(self, include_exam: bool = False) -> dict:
        """
        转换为字典，可包含关联的试卷信息
        
        Args:
            include_exam: 是否包含试卷信息
            
        Returns:
            包含题目信息的字典
        """
        data = super().to_dict()
        
        # 处理JSON字段
        if 'options' in data and data['options']:
            if isinstance(data['options'], str):
                try:
                    data['options'] = json.loads(data['options'])
                except json.JSONDecodeError:
                    data['options'] = []
        
        if 'metadata' in data and data['metadata']:
            if isinstance(data['metadata'], str):
                try:
                    data['metadata'] = json.loads(data['metadata'])
                except json.JSONDecodeError:
                    data['metadata'] = {}
        
        # 添加统计信息
        data['correct_rate'] = self.get_correct_rate()
        
        if include_exam and self.exam:
            data['exam_title'] = self.exam.title
        
        return data
    
    def __repr__(self) -> str:
        """友好的字符串表示"""
        return f'<Question id={self.id} type="{self.type}" exam_id={self.exam_id}>'