"""科目模型"""

from typing import List, Optional
from app.extensions import db
from .base import BaseModel


class Subject(BaseModel):
    """
    科目模型
    
    表示一个学科领域，如Python、C++、Java等
    """
    
    __tablename__ = 'subjects'
    
    # 字段定义
    name = db.Column(
        db.String(50), 
        nullable=False, 
        unique=True,
        doc='科目名称（如Python、C++、Java）'
    )
    description = db.Column(
        db.Text,
        nullable=True,
        doc='科目描述'
    )
    is_active = db.Column(
        db.Boolean,
        default=True,
        nullable=False,
        doc='是否启用'
    )
    order_index = db.Column(
        db.Integer,
        default=0,
        nullable=False,
        doc='排序索引'
    )
    
    # 关系定义
    exams = db.relationship(
        'Exam',
        back_populates='subject',
        lazy='dynamic',
        cascade='all, delete-orphan',
        doc='关联的试卷'
    )
    
    def __init__(
        self,
        name: str,
        description: Optional[str] = None,
        is_active: bool = True,
        order_index: int = 0
    ):
        """
        初始化科目

        Args:
            name: 科目名称
            description: 科目描述（可选）
            is_active: 是否启用，默认True
            order_index: 排序索引，默认0
        """
        self.name = name
        self.description = description
        self.is_active = is_active
        self.order_index = order_index
    
    @classmethod
    def get_by_name(cls, name: str) -> Optional['Subject']:
        """
        根据名称获取科目
        
        Args:
            name: 科目名称
            
        Returns:
            科目实例，如果不存在则返回None
        """
        return cls.query.filter_by(name=name).first()
    
    @classmethod
    def get_all_names(cls) -> List[str]:
        """
        获取所有科目名称
        
        Returns:
            科目名称列表
        """
        subjects = cls.query.all()
        return [subject.name for subject in subjects]
    
    def get_exam_count(self) -> int:
        """
        获取该科目的试卷数量
        
        Returns:
            试卷数量
        """
        return self.exams.count()
    
    def to_dict(self, include_exams: bool = False) -> dict:
        """
        转换为字典，可包含关联的试卷
        
        Args:
            include_exams: 是否包含试卷信息
            
        Returns:
            包含科目信息的字典
        """
        data = super().to_dict()
        
        if include_exams:
            data['exam_count'] = self.get_exam_count()
            # 避免循环导入，只包含基本信息
            data['exams'] = [exam.to_dict() for exam in self.exams.limit(10).all()]
        
        return data
    
    def __repr__(self) -> str:
        """友好的字符串表示"""
        return f'<Subject id={self.id} name="{self.name}">'