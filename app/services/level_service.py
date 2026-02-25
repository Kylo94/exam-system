"""难度级别服务模块"""

from typing import List, Optional, Dict, Any
from flask_sqlalchemy import SQLAlchemy

from app.models import Level
from .base import BaseService


class LevelService(BaseService[Level]):
    """难度级别服务类"""
    
    def __init__(self, db: SQLAlchemy):
        """初始化难度级别服务"""
        super().__init__(Level, db)
    
    def get_by_name(self, name: str) -> Optional[Level]:
        """根据名称获取难度级别
        
        Args:
            name: 难度级别名称
            
        Returns:
            找到的难度级别或None
        """
        return Level.query.filter_by(name=name).first()
    
    def get_by_difficulty(self, difficulty: int) -> Optional[Level]:
        """根据难度值获取难度级别
        
        Args:
            difficulty: 难度值
            
        Returns:
            找到的难度级别或None
        """
        return Level.query.filter_by(difficulty=difficulty).first()
    
    def get_all_active(self) -> List[Level]:
        """获取所有活跃难度级别

        Returns:
            活跃难度级别列表
        """
        return Level.query.filter_by(is_active=True).order_by(Level.order_index).all()
    
    def create_level(self, name: str, difficulty: int, 
                     description: str = "", is_active: bool = True) -> Level:
        """创建新难度级别
        
        Args:
            name: 难度级别名称
            difficulty: 难度值（数字越小越简单）
            description: 描述
            is_active: 是否活跃
            
        Returns:
            创建的难度级别
            
        Raises:
            ValueError: 难度级别名称或难度值已存在
        """
        # 检查名称是否已存在
        existing_by_name = self.get_by_name(name)
        if existing_by_name:
            raise ValueError(f"难度级别名称 '{name}' 已存在")
        
        # 检查难度值是否已存在
        existing_by_difficulty = self.get_by_difficulty(difficulty)
        if existing_by_difficulty:
            raise ValueError(f"难度值 {difficulty} 已存在")
        
        return self.create({
            'name': name,
            'difficulty': difficulty,
            'description': description,
            'is_active': is_active
        })
    
    def update_level(self, id: int, **kwargs) -> Optional[Level]:
        """更新难度级别信息
        
        Args:
            id: 难度级别ID
            **kwargs: 更新字段
            
        Returns:
            更新后的难度级别或None
            
        Raises:
            ValueError: 难度级别名称或难度值已存在
        """
        instance = self.get_by_id(id)
        if not instance:
            return None
        
        if 'name' in kwargs and kwargs['name'] != instance.name:
            existing = self.get_by_name(kwargs['name'])
            if existing and existing.id != id:
                raise ValueError(f"难度级别名称 '{kwargs['name']}' 已存在")
        
        if 'difficulty' in kwargs and kwargs['difficulty'] != instance.difficulty:
            existing = self.get_by_difficulty(kwargs['difficulty'])
            if existing and existing.id != id:
                raise ValueError(f"难度值 {kwargs['difficulty']} 已存在")
        
        return self.update(id, kwargs)
    
    def search_levels(self, name: Optional[str] = None,
                     is_active: Optional[bool] = None,
                     skip: int = 0, limit: int = 100) -> List[Level]:
        """搜索难度级别

        Args:
            name: 难度级别名称（模糊搜索）
            is_active: 是否活跃
            skip: 跳过的记录数
            limit: 返回的最大记录数

        Returns:
            难度级别列表
        """
        query = Level.query

        if name:
            query = query.filter(Level.name.ilike(f"%{name}%"))

        if is_active is not None:
            query = query.filter_by(is_active=is_active)

        query = query.order_by(Level.order_index)

        return query.offset(skip).limit(limit).all()
    
    def get_next_order_index(self) -> int:
        """获取下一个可用的排序索引

        Returns:
            下一个排序索引
        """
        max_order_index = self.db.session.query(self.db.func.max(Level.order_index)).scalar()
        return (max_order_index or 0) + 1