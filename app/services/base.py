"""基础服务类

提供通用的CRUD操作和数据库会话管理。
"""

from typing import Type, TypeVar, Generic, List, Optional, Dict, Any
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import Session

from app.models.base import BaseModel

ModelType = TypeVar('ModelType', bound=BaseModel)


class BaseService(Generic[ModelType]):
    """基础服务类，提供通用CRUD操作"""
    
    def __init__(self, model: Type[ModelType], db: SQLAlchemy):
        """初始化服务
        
        Args:
            model: SQLAlchemy模型类
            db: SQLAlchemy数据库实例
        """
        self.model = model
        self.db = db
    
    def get_session(self) -> Session:
        """获取数据库会话"""
        return self.db.session
    
    def get_by_id(self, id: int) -> Optional[ModelType]:
        """根据ID获取记录
        
        Args:
            id: 记录ID
            
        Returns:
            找到的记录或None
        """
        return self.model.query.get(id)
    
    def get_all(self, skip: int = 0, limit: int = 100) -> List[ModelType]:
        """获取所有记录（支持分页）
        
        Args:
            skip: 跳过的记录数
            limit: 返回的最大记录数
            
        Returns:
            记录列表
        """
        return self.model.query.offset(skip).limit(limit).all()
    
    def create(self, data: Dict[str, Any]) -> ModelType:
        """创建新记录
        
        Args:
            data: 记录数据字典
            
        Returns:
            创建的记录
            
        Raises:
            ValueError: 数据验证失败
        """
        # 验证数据
        self._validate_create_data(data)
        
        # 创建记录
        instance = self.model(**data)
        self.db.session.add(instance)
        self.db.session.commit()
        return instance
    
    def update(self, id: int, data: Dict[str, Any]) -> Optional[ModelType]:
        """更新记录
        
        Args:
            id: 记录ID
            data: 更新数据字典
            
        Returns:
            更新后的记录或None（如果记录不存在）
            
        Raises:
            ValueError: 数据验证失败
        """
        instance = self.get_by_id(id)
        if not instance:
            return None
        
        # 验证数据
        self._validate_update_data(data, instance)
        
        # 更新字段
        for key, value in data.items():
            if hasattr(instance, key):
                setattr(instance, key, value)
        
        instance.update()  # 更新updated_at时间戳
        self.db.session.commit()
        return instance
    
    def delete(self, id: int) -> bool:
        """删除记录
        
        Args:
            id: 记录ID
            
        Returns:
            是否成功删除
        """
        instance = self.get_by_id(id)
        if not instance:
            return False
        
        self.db.session.delete(instance)
        self.db.session.commit()
        return True
    
    def search(self, filters: Dict[str, Any], skip: int = 0, limit: int = 100) -> List[ModelType]:
        """根据条件搜索记录
        
        Args:
            filters: 过滤条件字典
            skip: 跳过的记录数
            limit: 返回的最大记录数
            
        Returns:
            符合条件的记录列表
        """
        query = self.model.query
        
        for key, value in filters.items():
            if hasattr(self.model, key):
                column = getattr(self.model, key)
                if isinstance(value, (list, tuple)):
                    query = query.filter(column.in_(value))
                else:
                    query = query.filter(column == value)
        
        return query.offset(skip).limit(limit).all()
    
    def count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """统计记录数量
        
        Args:
            filters: 过滤条件字典（可选）
            
        Returns:
            记录数量
        """
        query = self.model.query
        
        if filters:
            for key, value in filters.items():
                if hasattr(self.model, key):
                    column = getattr(self.model, key)
                    if isinstance(value, (list, tuple)):
                        query = query.filter(column.in_(value))
                    else:
                        query = query.filter(column == value)
        
        return query.count()
    
    def _validate_create_data(self, data: Dict[str, Any]) -> None:
        """验证创建数据
        
        Args:
            data: 创建数据
            
        Raises:
            ValueError: 数据验证失败
        """
        # 子类可以重写此方法实现具体验证逻辑
        required_fields = []
        for column in self.model.__table__.columns:
            # 跳过主键字段
            if column.primary_key:
                continue
            # 跳过有默认值的字段（如created_at, updated_at）
            if column.default is not None or column.server_default is not None:
                continue
            # 跳过自动递增字段
            if column.autoincrement:
                continue
            # 显式跳过自动生成的时间戳字段
            if column.name in ['created_at', 'updated_at']:
                continue
            # 只检查不可为空的字段
            if not column.nullable:
                required_fields.append(column.name)
        
        for field in required_fields:
            if field not in data:
                raise ValueError(f"缺少必填字段: {field}")
    
    def _validate_update_data(self, data: Dict[str, Any], instance: ModelType) -> None:
        """验证更新数据
        
        Args:
            data: 更新数据
            instance: 现有记录实例
            
        Raises:
            ValueError: 数据验证失败
        """
        # 子类可以重写此方法实现具体验证逻辑
        pass