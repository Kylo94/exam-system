"""等级模型"""

from typing import List, Optional
from app.extensions import db
from .base import BaseModel


class Level(BaseModel):
    """
    等级模型

    表示难度等级，如一级、二级、三级等
    等级属于科目，一个科目可以包含多个等级
    """

    __tablename__ = 'levels'

    # 字段定义
    subject_id = db.Column(
        db.Integer,
        db.ForeignKey('subjects.id', ondelete='CASCADE'),
        nullable=False,
        doc='所属科目ID'
    )
    name = db.Column(
        db.String(50),
        nullable=False,
        doc='等级名称（如一级、二级、三级）'
    )
    description = db.Column(
        db.Text,
        nullable=True,
        doc='等级描述'
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
    subject = db.relationship(
        'Subject',
        back_populates='levels',
        lazy='joined',
        doc='所属科目'
    )
    
    # 关系定义
    exams = db.relationship(
        'Exam',
        back_populates='level',
        lazy='dynamic',
        cascade='all, delete-orphan',
        doc='关联的试卷'
    )

    def __init__(
        self,
        subject_id: int,
        name: str,
        description: Optional[str] = None,
        is_active: bool = True,
        order_index: int = 0
    ):
        """
        初始化等级

        Args:
            subject_id: 所属科目ID
            name: 等级名称
            description: 等级描述（可选）
            is_active: 是否启用，默认True
            order_index: 排序索引，默认0
        """
        self.subject_id = subject_id
        self.name = name
        self.description = description
        self.is_active = is_active
        self.order_index = order_index

    @classmethod
    def get_by_subject_and_name(cls, subject_id: int, name: str) -> Optional['Level']:
        """
        根据科目ID和名称获取等级

        Args:
            subject_id: 科目ID
            name: 等级名称

        Returns:
            等级实例，如果不存在则返回None
        """
        return cls.query.filter_by(subject_id=subject_id, name=name).first()

    @classmethod
    def get_by_subject(cls, subject_id: int) -> List['Level']:
        """
        获取指定科目的所有等级

        Args:
            subject_id: 科目ID

        Returns:
            等级列表
        """
        return cls.query.filter_by(subject_id=subject_id).order_by(cls.order_index).all()

    @classmethod
    def get_by_name(cls, name: str) -> Optional['Level']:
        """
        根据名称获取等级（已废弃，请使用 get_by_subject_and_name）

        Args:
            name: 等级名称

        Returns:
            等级实例，如果不存在则返回None
        """
        return cls.query.filter_by(name=name).first()

    @classmethod
    def get_all_names(cls) -> List[str]:
        """
        获取所有等级名称（已废弃）

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

    def get_subject_name(self) -> Optional[str]:
        """
        获取所属科目名称

        Returns:
            科目名称，如果没有关联科目则返回None
        """
        return self.subject.name if self.subject else None

    def to_dict(self, include_exams: bool = False, include_subject: bool = False) -> dict:
        """
        转换为字典，可包含关联的试卷

        Args:
            include_exams: 是否包含试卷信息
            include_subject: 是否包含科目信息

        Returns:
            包含等级信息的字典
        """
        data = super().to_dict()
        data['subject_id'] = self.subject_id

        if include_subject:
            data['subject_name'] = self.get_subject_name()

        if include_exams:
            data['exam_count'] = self.get_exam_count()
            # 避免循环导入，只包含基本信息
            data['exams'] = [exam.to_dict() for exam in self.exams.limit(10).all()]

        return data

    def __repr__(self) -> str:
        """友好的字符串表示"""
        return f'<Level id={self.id} name="{self.name}" subject_id={self.subject_id}>'