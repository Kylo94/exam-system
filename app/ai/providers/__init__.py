"""AI提供商模块"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class BaseProvider(ABC):
    """AI提供商基类"""
    
    def __init__(self, api_key: str, base_url: str):
        """初始化提供商
        
        Args:
            api_key: API密钥
            base_url: API基础URL
        """
        self.api_key = api_key
        self.base_url = base_url
    
    @abstractmethod
    def chat_completion(self, messages: list, **kwargs) -> str:
        """聊天补全
        
        Args:
            messages: 消息列表
            **kwargs: 其他参数
            
        Returns:
            模型回复
        """
        pass
    
    @abstractmethod
    def embeddings(self, text: str) -> List[float]:
        """获取文本嵌入
        
        Args:
            text: 文本
            
        Returns:
            嵌入向量
        """
        pass