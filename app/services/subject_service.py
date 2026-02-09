"""科目服务模块"""

from typing import List, Optional, Dict, Any
from flask_sqlalchemy import SQLAlchemy

from app.models import Subject
from .base import BaseService


class SubjectService(BaseService[Subject]):
    """科目服务类"""
    
    def __init__(self, db: SQLAlchemy):
        """初始化科目服务"""
        super().__init__(Subject, db)
    
    def get_by_name(self, name: str) -> Optional[Subject]:
        """根据名称获取科目
        
        Args:
            name: 科目名称
            
        Returns:
            找到的科目或None
        """
        return Subject.query.filter_by(name=name).first()
    
    def get_all_active(self) -> List[Subject]:
        """获取所有活跃科目
        
        Returns:
            活跃科目列表
        """
        return Subject.query.filter_by(is_active=True).order_by(Subject.order_index).all()
    
    def create_subject(self, name: str, description: str = "", 
                       is_active: bool = True, order_index: int = 0) -> Subject:
        """创建新科目
        
        Args:
            name: 科目名称
            description: 科目描述
            is_active: 是否活跃
            order_index: 排序索引
            
        Returns:
            创建的科目
            
        Raises:
            ValueError: 科目名称已存在
        """
        # 检查名称是否已存在
        existing = self.get_by_name(name)
        if existing:
            raise ValueError(f"科目名称 '{name}' 已存在")
        
        return self.create({
            'name': name,
            'description': description,
            'is_active': is_active,
            'order_index': order_index
        })
    
    def update_subject(self, id: int, **kwargs) -> Optional[Subject]:
        """更新科目信息
        
        Args:
            id: 科目ID
            **kwargs: 更新字段
            
        Returns:
            更新后的科目或None
            
        Raises:
            ValueError: 科目名称已存在
        """
        if 'name' in kwargs:
            existing = self.get_by_name(kwargs['name'])
            if existing and existing.id != id:
                raise ValueError(f"科目名称 '{kwargs['name']}' 已存在")
        
        return self.update(id, kwargs)
    
    def search_subjects(self, name: Optional[str] = None, 
                       is_active: Optional[bool] = None,
                       skip: int = 0, limit: int = 100) -> List[Subject]:
        """搜索科目
        
        Args:
            name: 科目名称（模糊搜索）
            is_active: 是否活跃
            skip: 跳过的记录数
            limit: 返回的最大记录数
            
        Returns:
            科目列表
        """
        query = Subject.query
        
        if name:
            query = query.filter(Subject.name.ilike(f"%{name}%"))
        
        if is_active is not None:
            query = query.filter_by(is_active=is_active)
        
        query = query.order_by(Subject.order_index, Subject.name)
        
        return query.offset(skip).limit(limit).all()
    
    def count_active_subjects(self) -> int:
        """统计活跃科目数量
        
        Returns:
            活跃科目数量
        """
        return Subject.query.filter_by(is_active=True).count()