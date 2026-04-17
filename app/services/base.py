"""AI服务基类"""

import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class AIServiceBase:
    """AI服务基类"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.logger = logger
    
    def _log(self, level: str, message: str) -> None:
        """统一的日志记录"""
        getattr(self.logger, level)(message)
    
    async def initialize(self) -> None:
        """初始化服务"""
        pass
    
    async def cleanup(self) -> None:
        """清理资源"""
        pass
