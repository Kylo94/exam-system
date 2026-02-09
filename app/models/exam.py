"""试卷模型"""

from typing import Dict, List, Optional
from datetime import datetime
from app.extensions import db
from .base import BaseModel


class Exam(BaseModel):
    """
    试卷模型
    
    表示一套完整的试卷，包含多个题目
    """
    
    __tablename__ = 'exams'
    
    # 字段定义
    title = db.Column(
        db.String(200),
        nullable=False,
        doc='试卷标题'
    )
    subject_id = db.Column(
        db.Integer,
        db.ForeignKey('subjects.id', ondelete='SET NULL'),
        nullable=True,
        doc='科目ID'
    )
    level_id = db.Column(
        db.Integer,
        db.ForeignKey('levels.id', ondelete='SET NULL'),
        nullable=True,
        doc='等级ID'
    )
    total_points = db.Column(
        db.Integer,
        default=100,
        nullable=False,
        doc='总分'
    )
    question_count = db.Column(
        db.Integer,
        default=0,
        nullable=False,
        doc='题目数量'
    )
    has_images = db.Column(
        db.Boolean,
        default=False,
        nullable=False,
        doc='是否包含图片'
    )
    file_path = db.Column(
        db.String(500),
        nullable=True,
        doc='原始文件路径'
    )
    
    # 关系定义
    subject = db.relationship(
        'Subject',
        back_populates='exams',
        lazy='joined',
        doc='关联的科目'
    )
    level = db.relationship(
        'Level',
        back_populates='exams',
        lazy='joined',
        doc='关联的等级'
    )
    questions = db.relationship(
        'Question',
        back_populates='exam',
        lazy='dynamic',
        cascade='all, delete-orphan',
        order_by='Question.order_num',
        doc='关联的题目'
    )
    submissions = db.relationship(
        'Submission',
        back_populates='exam',
        lazy='dynamic',
        cascade='all, delete-orphan',
        doc='关联的答题提交'
    )
    
    def __init__(
        self,
        title: str,
        subject_id: Optional[int] = None,
        level_id: Optional[int] = None,
        total_points: int = 100,
        file_path: Optional[str] = None
    ):
        """
        初始化试卷
        
        Args:
            title: 试卷标题
            subject_id: 科目ID（可选）
            level_id: 等级ID（可选）
            total_points: 总分，默认100
            file_path: 原始文件路径（可选）
        """
        self.title = title
        self.subject_id = subject_id
        self.level_id = level_id
        self.total_points = total_points
        self.file_path = file_path
        self.question_count = 0
        self.has_images = False
    
    @classmethod
    def get_by_title(cls, title: str) -> Optional['Exam']:
        """
        根据标题获取试卷
        
        Args:
            title: 试卷标题
            
        Returns:
            试卷实例，如果不存在则返回None
        """
        return cls.query.filter_by(title=title).first()
    
    @classmethod
    def search(
        cls,
        keyword: Optional[str] = None,
        subject_id: Optional[int] = None,
        level_id: Optional[int] = None,
        limit: int = 20,
        offset: int = 0
    ) -> List['Exam']:
        """
        搜索试卷
        
        Args:
            keyword: 关键词（在标题中搜索）
            subject_id: 科目ID筛选
            level_id: 等级ID筛选
            limit: 返回数量限制
            offset: 偏移量
            
        Returns:
            试卷列表
        """
        query = cls.query
        
        if keyword:
            query = query.filter(cls.title.ilike(f'%{keyword}%'))
        
        if subject_id:
            query = query.filter_by(subject_id=subject_id)
        
        if level_id:
            query = query.filter_by(level_id=level_id)
        
        return query.order_by(cls.created_at.desc()).offset(offset).limit(limit).all()
    
    def update_statistics(self) -> None:
        """更新试卷统计信息（题目数量、是否有图片）"""
        self.question_count = self.questions.count()
        self.has_images = any(question.has_image for question in self.questions.all())
        self.updated_at = datetime.utcnow()
        db.session.commit()
    
    def get_subject_name(self) -> Optional[str]:
        """
        获取科目名称
        
        Returns:
            科目名称，如果没有关联科目则返回None
        """
        return self.subject.name if self.subject else None
    
    def get_level_name(self) -> Optional[str]:
        """
        获取等级名称
        
        Returns:
            等级名称，如果没有关联等级则返回None
        """
        return self.level.name if self.level else None
    
    def get_average_score(self) -> Optional[float]:
        """
        获取平均分
        
        Returns:
            平均分，如果没有提交记录则返回None
        """
        submissions = self.submissions.filter_by(is_completed=True).all()
        if not submissions:
            return None
        
        total = sum(sub.total_score for sub in submissions)
        return total / len(submissions)
    
    def to_dict(self, include_questions: bool = False) -> dict:
        """
        转换为字典，可包含关联的题目
        
        Args:
            include_questions: 是否包含题目信息
            
        Returns:
            包含试卷信息的字典
        """
        data = super().to_dict()
        
        # 添加关联对象信息
        data['subject_name'] = self.get_subject_name()
        data['level_name'] = self.get_level_name()
        
        if include_questions:
            data['questions'] = [q.to_dict() for q in self.questions.all()]
        
        # 添加统计信息
        data['average_score'] = self.get_average_score()
        data['submission_count'] = self.submissions.count()
        
        return data
    
    def __repr__(self) -> str:
        """友好的字符串表示"""
        return f'<Exam id={self.id} title="{self.title}">'