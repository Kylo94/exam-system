"""等级模型"""

from typing import List, Optional
from app.extensions import db
from .base import BaseModel


class Level(BaseModel):
    """
    等级模型
    
    表示难度等级，如一级、二级、三级等
    """
    
    __tablename__ = 'levels'
    
    # 字段定义
    name = db.Column(
        db.String(50), 
        nullable=False, 
        unique=True,
        doc='等级名称（如一级、二级、三级）'
    )
    description = db.Column(
        db.Text,
        nullable=True,
        doc='等级描述'
    )
    
    # 关系定义
    exams = db.relationship(
        'Exam',
        back_populates='level',
        lazy='dynamic',
        cascade='all, delete-orphan',
        doc='关联的试卷'
    )
    
    def __init__(self, name: str, description: Optional[str] = None):
        """
        初始化等级
        
        Args:
            name: 等级名称
            description: 等级描述（可选）
        """
        self.name = name
        self.description = description
    
    @classmethod
    def get_by_name(cls, name: str) -> Optional['Level']:
        """
        根据名称获取等级
        
        Args:
            name: 等级名称
            
        Returns:
            等级实例，如果不存在则返回None
        """
        return cls.query.filter_by(name=name).first()
    
    @classmethod
    def get_all_names(cls) -> List[str]:
        """
        获取所有等级名称
        
        Returns:
            等级名称列表
        """
        levels = cls.query.all()
        return [level.name for level in levels]
    
    def get_exam_count(self) -> int:
        """
        获取该等级的试卷数量
        
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
            包含等级信息的字典
        """
        data = super().to_dict()
        
        if include_exams:
            data['exam_count'] = self.get_exam_count()
            # 避免循环导入，只包含基本信息
            data['exams'] = [exam.to_dict() for exam in self.exams.limit(10).all()]
        
        return data
    
    def __repr__(self) -> str:
        """友好的字符串表示"""
        return f'<Level id={self.id} name="{self.name}">'