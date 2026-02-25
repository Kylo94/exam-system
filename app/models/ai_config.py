"""AI配置模型"""

from app.models.base import BaseModel, db
from datetime import datetime


class AIConfig(BaseModel):
    """AI配置模型"""

    __tablename__ = 'ai_configs'

    id = db.Column(db.Integer, primary_key=True)
    provider = db.Column(db.String(50), nullable=False, default='deepseek')  # AI提供商：deepseek, openai, etc.
    api_key = db.Column(db.String(500), nullable=False)  # API密钥
    api_url = db.Column(db.String(500), nullable=False)  # API地址
    model = db.Column(db.String(100), nullable=False, default='deepseek-chat')  # 模型名称
    max_tokens = db.Column(db.Integer, default=2000)  # 最大token数
    temperature = db.Column(db.Float, default=0.7)  # 温度参数

    # 状态
    is_active = db.Column(db.Boolean, default=True, nullable=False)  # 是否启用
    is_default = db.Column(db.Boolean, default=False, nullable=False)  # 是否为默认配置

    # 元数据
    description = db.Column(db.String(500))  # 配置描述
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))  # 创建者
    last_used_at = db.Column(db.DateTime)  # 最后使用时间

    # 关系
    creator = db.relationship('User', backref=db.backref('ai_configs', lazy='dynamic'))

    def __repr__(self):
        return f'<AIConfig {self.provider} - {self.model}>'

    def to_dict(self):
        """转换为字典（不包含敏感信息）"""
        return {
            'id': self.id,
            'provider': self.provider,
            'api_url': self.api_url,
            'model': self.model,
            'max_tokens': self.max_tokens,
            'temperature': self.temperature,
            'is_active': self.is_active,
            'is_default': self.is_default,
            'description': self.description,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_used_at': self.last_used_at.isoformat() if self.last_used_at else None
        }

    def to_dict_with_key(self):
        """转换为字典（包含API密钥）"""
        data = self.to_dict()
        data['api_key'] = self.api_key
        data['created_by'] = self.created_by
        return data

    @staticmethod
    def get_active_provider():
        """获取当前启用的AI配置"""
        # 优先返回默认配置
        config = AIConfig.query.filter_by(
            is_active=True,
            is_default=True
        ).first()

        if config:
            return config

        # 如果没有默认配置，返回第一个激活的配置
        config = AIConfig.query.filter_by(
            is_active=True
        ).first()

        return config

    @staticmethod
    def set_default(config_id):
        """设置默认配置"""
        # 取消其他配置的默认状态
        AIConfig.query.filter_by(is_default=True).update({'is_default': False})

        # 设置新的默认配置
        config = AIConfig.query.get(config_id)
        if config:
            config.is_default = True
            db.session.commit()
            return config

        return None

    def update_last_used(self):
        """更新最后使用时间"""
        self.last_used_at = datetime.utcnow()
        db.session.commit()
