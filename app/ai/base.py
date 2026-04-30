"""AI服务基类"""

import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class BaseAIService:
    """AI服务基类"""
    
    def __init__(self, provider: str = "deepseek", config: Optional[Dict[str, Any]] = None):
        self.provider = provider
        self.config = config or {}
        self.logger = logger
