"""考点服务"""

from typing import List, Optional, Dict, Any
from sqlalchemy import func, desc, asc
from app.models import KnowledgePoint


class KnowledgePointService:
    """考点服务类"""

    def __init__(self, db):
        self.db = db

    def create(self, data: Dict[str, Any]) -> KnowledgePoint:
        """
        创建考点

        Args:
            data: 考点数据字典

        Returns:
            创建的考点对象
        """
        knowledge_point = KnowledgePoint(
            name=data['name'],
            code=data['code'],
            subject_id=data['subject_id'],
            level_id=data.get('level_id'),
            description=data.get('description'),
            parent_id=data.get('parent_id'),
            order_index=data.get('order_index', 0),
            is_active=data.get('is_active', True)
        )

        self.db.session.add(knowledge_point)
        self.db.session.commit()
        return knowledge_point

    def update(self, knowledge_point: KnowledgePoint, data: Dict[str, Any]) -> KnowledgePoint:
        """
        更新考点

        Args:
            knowledge_point: 考点对象
            data: 更新数据字典

        Returns:
            更新后的考点对象
        """
        if 'name' in data:
            knowledge_point.name = data['name']
        if 'code' in data:
            knowledge_point.code = data['code']
        if 'subject_id' in data:
            knowledge_point.subject_id = data['subject_id']
        if 'level_id' in data:
            knowledge_point.level_id = data['level_id']
        if 'description' in data:
            knowledge_point.description = data['description']
        if 'parent_id' in data:
            knowledge_point.parent_id = data['parent_id']
        if 'order_index' in data:
            knowledge_point.order_index = data['order_index']
        if 'is_active' in data:
            knowledge_point.is_active = data['is_active']

        self.db.session.commit()
        return knowledge_point

    def delete(self, knowledge_point: KnowledgePoint) -> bool:
        """
        删除考点

        Args:
            knowledge_point: 考点对象

        Returns:
            是否删除成功
        """
        try:
            self.db.session.delete(knowledge_point)
            self.db.session.commit()
            return True
        except Exception:
            self.db.session.rollback()
            return False

    def get_by_id(self, knowledge_point_id: int) -> Optional[KnowledgePoint]:
        """
        根据ID获取考点

        Args:
            knowledge_point_id: 考点ID

        Returns:
            考点对象
        """
        return KnowledgePoint.query.get(knowledge_point_id)

    def get_by_code(self, code: str) -> Optional[KnowledgePoint]:
        """
        根据代码获取考点

        Args:
            code: 考点代码

        Returns:
            考点对象
        """
        return KnowledgePoint.query.filter_by(code=code).first()

    def get_by_subject(
        self,
        subject_id: int,
        is_active: bool = True
    ) -> List[KnowledgePoint]:
        """
        根据科目获取考点列表

        Args:
            subject_id: 科目ID
            is_active: 是否只获取启用的考点

        Returns:
            考点列表
        """
        query = KnowledgePoint.query.filter_by(subject_id=subject_id)
        if is_active is not None:
            query = query.filter_by(is_active=is_active)
        return query.order_by(KnowledgePoint.order_index).all()

    def get_by_level(
        self,
        level_id: int,
        is_active: bool = True
    ) -> List[KnowledgePoint]:
        """
        根据难度等级获取考点列表

        Args:
            level_id: 难度等级ID
            is_active: 是否只获取启用的考点

        Returns:
            考点列表
        """
        query = KnowledgePoint.query.filter_by(level_id=level_id)
        if is_active is not None:
            query = query.filter_by(is_active=is_active)
        return query.order_by(KnowledgePoint.order_index).all()

    def get_by_subject_and_level(
        self,
        subject_id: int,
        level_id: int,
        is_active: bool = True
    ) -> List[KnowledgePoint]:
        """
        根据科目和难度等级获取考点列表

        Args:
            subject_id: 科目ID
            level_id: 难度等级ID
            is_active: 是否只获取启用的考点

        Returns:
            考点列表
        """
        query = KnowledgePoint.query.filter_by(
            subject_id=subject_id,
            level_id=level_id
        )
        if is_active is not None:
            query = query.filter_by(is_active=is_active)
        return query.order_by(KnowledgePoint.order_index).all()

    def search_knowledge_points(
        self,
        name: Optional[str] = None,
        subject_id: Optional[int] = None,
        level_id: Optional[int] = None,
        is_active: Optional[bool] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[KnowledgePoint]:
        """
        搜索考点

        Args:
            name: 考点名称（模糊搜索）
            subject_id: 科目ID
            level_id: 难度等级ID
            is_active: 是否启用
            skip: 跳过的记录数
            limit: 返回的最大记录数

        Returns:
            考点列表
        """
        query = KnowledgePoint.query

        if name:
            query = query.filter(KnowledgePoint.name.ilike(f"%{name}%"))

        if subject_id:
            query = query.filter_by(subject_id=subject_id)

        if level_id:
            query = query.filter_by(level_id=level_id)

        if is_active is not None:
            query = query.filter_by(is_active=is_active)

        query = query.order_by(KnowledgePoint.order_index)

        return query.offset(skip).limit(limit).all()

    def count(self, filters: Dict[str, Any] = None) -> int:
        """
        统计考点数量

        Args:
            filters: 过滤条件

        Returns:
            考点总数
        """
        query = KnowledgePoint.query

        if filters:
            name = filters.get('name')
            subject_id = filters.get('subject_id')
            level_id = filters.get('level_id')
            is_active = filters.get('is_active')

            if name:
                query = query.filter(KnowledgePoint.name.ilike(f"%{name}%"))
            if subject_id:
                query = query.filter_by(subject_id=subject_id)
            if level_id:
                query = query.filter_by(level_id=level_id)
            if is_active is not None:
                query = query.filter_by(is_active=is_active)

        return query.count()

    def get_all_active(self) -> List[KnowledgePoint]:
        """
        获取所有启用的考点

        Returns:
            考点列表
        """
        return KnowledgePoint.query.filter_by(
            is_active=True
        ).order_by(KnowledgePoint.order_index).all()

    def get_next_order_index(self) -> int:
        """
        获取下一个可用的排序索引

        Returns:
            下一个排序索引
        """
        max_order_index = self.db.session.query(
            func.max(KnowledgePoint.order_index)
        ).scalar()
        return (max_order_index or 0) + 1
