"""基础模型类"""

from datetime import datetime
from typing import Any, Dict
from app.extensions import db


class BaseModel(db.Model):
    """
    所有模型的基类
    
    提供以下字段：
    - id: 主键
    - created_at: 创建时间
    - updated_at: 更新时间
    """
    
    __abstract__ = True
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime, 
        default=datetime.utcnow, 
        onupdate=datetime.utcnow,
        nullable=False
    )
    
    def to_dict(self) -> Dict[str, Any]:
        """
        将模型实例转换为字典
        
        Returns:
            包含模型字段的字典
        """
        result = {}
        for column in self.__table__.columns:
            value = getattr(self, column.name)
            
            # 处理特殊类型
            if isinstance(value, datetime):
                value = value.isoformat()
            
            result[column.name] = value
        
        return result
    
    def update(self, **kwargs) -> None:
        """
        更新模型字段
        
        Args:
            **kwargs: 要更新的字段和值
        """
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        
        db.session.commit()
    
    @classmethod
    def get_by_id(cls, id: int) -> 'BaseModel':
        """
        根据ID获取记录
        
        Args:
            id: 记录ID
            
        Returns:
            模型实例，如果不存在则返回None
        """
        return cls.query.get(id)
    
    def __repr__(self) -> str:
        """友好的字符串表示"""
        return f'<{self.__class__.__name__} id={self.id}>'