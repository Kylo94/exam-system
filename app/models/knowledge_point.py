"""考点模型"""

from typing import List, Optional
from app.extensions import db
from .base import BaseModel


class KnowledgePoint(BaseModel):
    """
    考点模型

    表示科目下的知识点/考点，用于题目分类和专项刷题
    """

    __tablename__ = 'knowledge_points'

    # 字段定义
    name = db.Column(
        db.String(200),
        nullable=False,
        doc='考点名称'
    )
    code = db.Column(
        db.String(50),
        nullable=False,
        unique=True,
        doc='考点代码，如 "tree-01" 用于标识'
    )
    subject_id = db.Column(
        db.Integer,
        db.ForeignKey('subjects.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
        doc='所属科目ID'
    )
    level_id = db.Column(
        db.Integer,
        db.ForeignKey('levels.id', ondelete='SET NULL'),
        nullable=True,
        index=True,
        doc='适用难度等级（可选）'
    )
    description = db.Column(
        db.Text,
        nullable=True,
        doc='考点描述'
    )
    parent_id = db.Column(
        db.Integer,
        db.ForeignKey('knowledge_points.id', ondelete='SET NULL'),
        nullable=True,
        doc='父考点ID（支持层级结构）'
    )
    order_index = db.Column(
        db.Integer,
        default=0,
        nullable=False,
        doc='排序序号'
    )
    is_active = db.Column(
        db.Boolean,
        default=True,
        nullable=False,
        doc='是否启用'
    )

    # 关系定义
    subject = db.relationship(
        'Subject',
        backref='knowledge_points',
        lazy='joined',
        doc='关联的科目'
    )
    level = db.relationship(
        'Level',
        backref='knowledge_points',
        lazy='joined',
        doc='关联的难度等级'
    )
    parent = db.relationship(
        'KnowledgePoint',
        remote_side='KnowledgePoint.id',
        backref='children',
        lazy='joined',
        doc='父考点'
    )

    def __init__(
        self,
        name: str,
        code: str,
        subject_id: int,
        level_id: Optional[int] = None,
        description: Optional[str] = None,
        parent_id: Optional[int] = None,
        order_index: int = 0,
        is_active: bool = True
    ):
        """
        初始化考点

        Args:
            name: 考点名称
            code: 考点代码
            subject_id: 所属科目ID
            level_id: 适用难度等级（可选）
            description: 考点描述（可选）
            parent_id: 父考点ID（可选）
            order_index: 排序序号
            is_active: 是否启用
        """
        self.name = name
        self.code = code
        self.subject_id = subject_id
        self.level_id = level_id
        self.description = description
        self.parent_id = parent_id
        self.order_index = order_index
        self.is_active = is_active

    @classmethod
    def get_by_subject(cls, subject_id: int) -> List['KnowledgePoint']:
        """
        根据科目ID获取所有考点

        Args:
            subject_id: 科目ID

        Returns:
            考点列表，按排序序号排序
        """
        return cls.query.filter_by(
            subject_id=subject_id,
            is_active=True
        ).order_by(cls.order_index).all()

    @classmethod
    def get_by_level(cls, level_id: int) -> List['KnowledgePoint']:
        """
        根据难度等级获取所有考点

        Args:
            level_id: 难度等级ID

        Returns:
            考点列表，按排序序号排序
        """
        return cls.query.filter_by(
            level_id=level_id,
            is_active=True
        ).order_by(cls.order_index).all()

    @classmethod
    def get_by_subject_and_level(cls, subject_id: int, level_id: int) -> List['KnowledgePoint']:
        """
        根据科目和难度等级获取考点

        Args:
            subject_id: 科目ID
            level_id: 难度等级ID

        Returns:
            考点列表，按排序序号排序
        """
        return cls.query.filter_by(
            subject_id=subject_id,
            level_id=level_id,
            is_active=True
        ).order_by(cls.order_index).all()

    def get_tree(self) -> List['KnowledgePoint']:
        """
        获取考点树（包含所有子考点）

        Returns:
            包含当前考点和所有子考点的列表
        """
        tree = [self]
        for child in self.children:
            tree.extend(child.get_tree())
        return tree

    def to_dict(self, include_parent: bool = False, include_children: bool = False) -> dict:
        """
        转换为字典

        Args:
            include_parent: 是否包含父考点信息
            include_children: 是否包含子考点信息

        Returns:
            包含考点信息的字典
        """
        data = super().to_dict()

        if include_parent and self.parent:
            data['parent'] = {
                'id': self.parent.id,
                'name': self.parent.name,
                'code': self.parent.code
            }

        if include_children and self.children:
            data['children'] = [
                {
                    'id': child.id,
                    'name': child.name,
                    'code': child.code
                }
                for child in self.children
            ]

        if self.subject:
            data['subject_name'] = self.subject.name

        if self.level:
            data['level_name'] = self.level.name

        return data

    def __repr__(self) -> str:
        """友好的字符串表示"""
        return f'<KnowledgePoint id={self.id} code="{self.code}" name="{self.name}">'
