"""DeepSeek AI提供商"""

import json
from typing import Any, Dict, List, Optional
import requests
from . import BaseProvider


class DeepSeekProvider(BaseProvider):
    """DeepSeek AI提供商"""
    
    def __init__(self, api_key: str, base_url: str = 'https://api.deepseek.com'):
        """初始化DeepSeek提供商
        
        Args:
            api_key: DeepSeek API密钥
            base_url: API基础URL
        """
        super().__init__(api_key, base_url)
        self.headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }
    
    def chat_completion(self, messages: list, **kwargs) -> str:
        """DeepSeek聊天补全
        
        Args:
            messages: 消息列表
            **kwargs: 其他参数
            
        Returns:
            模型回复
            
        Raises:
            Exception: API调用失败
        """
        url = f'{self.base_url}/chat/completions'
        
        # 构建请求数据
        data = {
            'model': kwargs.get('model', 'deepseek-chat'),
            'messages': messages,
            'temperature': kwargs.get('temperature', 0.7),
            'max_tokens': kwargs.get('max_tokens', 2000),
            'stream': kwargs.get('stream', False)
        }
        
        # 过滤None值
        data = {k: v for k, v in data.items() if v is not None}
        
        try:
            response = requests.post(url, headers=self.headers, json=data, timeout=60)
            response.raise_for_status()
            result = response.json()
            
            # 提取回复内容
            return result['choices'][0]['message']['content']
        except requests.exceptions.RequestException as e:
            raise Exception(f'DeepSeek API调用失败: {str(e)}')
        except (KeyError, IndexError) as e:
            raise Exception(f'DeepSeek API响应解析失败: {str(e)}')
    
    def embeddings(self, text: str) -> List[float]:
        """获取文本嵌入（DeepSeek暂不支持嵌入，返回空列表）
        
        Args:
            text: 文本
            
        Returns:
            嵌入向量
        """
        # DeepSeek目前不提供嵌入API
        return []