"""AI服务基类"""

import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class BaseProvider:
    """AI提供商基类"""
    
    def __init__(self, api_key: str, base_url: str = ""):
        self.api_key = api_key
        self.base_url = base_url


class BaseAIService:
    """AI服务基类"""
    
    def __init__(self, provider: str = "deepseek", config: Optional[Dict[str, Any]] = None):
        self.provider = provider
        self.config = config or {}
        self.logger = logger
