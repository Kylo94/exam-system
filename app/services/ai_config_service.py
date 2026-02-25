"""AI配置服务"""

from app.services.base import BaseService
from app.models.ai_config import AIConfig


class AIConfigService(BaseService):
    """AI配置服务"""

    model_class = AIConfig

    def __init__(self, db):
        """初始化服务

        Args:
            db: SQLAlchemy数据库实例
        """
        super().__init__(self.model_class, db)

    def create_ai_config(
        self,
        provider: str,
        api_key: str,
        api_url: str,
        model: str = 'deepseek-chat',
        max_tokens: int = 2000,
        temperature: float = 0.7,
        description: str = '',
        is_active: bool = True,
        is_default: bool = False,
        created_by: int = None
    ) -> AIConfig:
        """
        创建AI配置

        Args:
            provider: AI提供商
            api_key: API密钥
            api_url: API地址
            model: 模型名称
            max_tokens: 最大token数
            temperature: 温度参数
            description: 描述
            is_active: 是否激活
            is_default: 是否默认
            created_by: 创建者ID

        Returns:
            创建的AI配置
        """
        # 如果设置为默认，取消其他配置的默认状态
        if is_default:
            AIConfig.query.filter_by(is_default=True).update({'is_default': False})

        config = AIConfig(
            provider=provider,
            api_key=api_key,
            api_url=api_url,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            description=description,
            is_active=is_active,
            is_default=is_default,
            created_by=created_by
        )

        self.db.session.add(config)
        self.db.session.commit()

        return config

    def update_ai_config(
        self,
        config_id: int,
        **kwargs
    ) -> AIConfig:
        """
        更新AI配置

        Args:
            config_id: 配置ID
            **kwargs: 更新字段

        Returns:
            更新后的AI配置
        """
        config = self.get_by_id(config_id)
        if not config:
            return None

        # 如果设置为默认，取消其他配置的默认状态
        if kwargs.get('is_default', False):
            AIConfig.query.filter_by(is_default=True).update({'is_default': False})

        # 更新字段
        updatable_fields = [
            'provider', 'api_key', 'api_url', 'model',
            'max_tokens', 'temperature', 'description',
            'is_active', 'is_default'
        ]

        for field in updatable_fields:
            if field in kwargs:
                setattr(config, field, kwargs[field])

        self.db.session.commit()

        return config

    def search_ai_configs(
        self,
        provider: str = None,
        is_active: bool = None,
        is_default: bool = None,
        skip: int = 0,
        limit: int = 10
    ) -> list:
        """
        搜索AI配置

        Args:
            provider: 提供商
            is_active: 是否激活
            is_default: 是否默认
            skip: 跳过数量
            limit: 限制数量

        Returns:
            AI配置列表
        """
        query = AIConfig.query

        if provider:
            query = query.filter_by(provider=provider)

        if is_active is not None:
            query = query.filter_by(is_active=is_active)

        if is_default is not None:
            query = query.filter_by(is_default=is_default)

        return query.order_by(AIConfig.created_at.desc()).offset(skip).limit(limit).all()

    def count(self, filters: dict = None) -> int:
        """
        统计AI配置数量

        Args:
            filters: 过滤条件

        Returns:
            数量
        """
        query = AIConfig.query

        if filters:
            if 'provider' in filters:
                query = query.filter_by(provider=filters['provider'])
            if 'is_active' in filters:
                query = query.filter_by(is_active=filters['is_active'])
            if 'is_default' in filters:
                query = query.filter_by(is_default=filters['is_default'])

        return query.count()
