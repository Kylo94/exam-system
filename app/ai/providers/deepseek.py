"""DeepSeek AI提供商 - 使用 OpenAI SDK"""

from typing import List
from openai import OpenAI
from . import BaseProvider


class DeepSeekProvider(BaseProvider):
    """DeepSeek AI提供商 - 基于 OpenAI SDK"""

    def __init__(self, api_key: str, base_url: str = 'https://api.deepseek.com'):
        """初始化DeepSeek提供商

        Args:
            api_key: DeepSeek API密钥
            base_url: API基础URL
        """
        super().__init__(api_key, base_url)
        self._client = None

    @property
    def client(self):
        """获取 OpenAI 客户端"""
        if self._client is None:
            self._client = OpenAI(
                api_key=self.api_key,
                base_url=self.base_url
            )
        return self._client

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
        model = kwargs.get('model', 'deepseek-v4-pro')
        temperature = kwargs.get('temperature', 0.3)
        max_tokens = kwargs.get('max_tokens', 4096)  # 默认使用4096，让API决定上限

        # 构建请求参数
        request_kwargs = {
            'model': model,
            'messages': messages,
            'temperature': temperature,
            'max_tokens': max_tokens,
            'stream': False
        }

        # 对于deepseek-v4-flash模型，支持thinking参数
        if 'deepseek-v4-flash' in model:
            request_kwargs['extra_body'] = {
                'thinking': {'type': 'enabled'}
            }

        try:
            response = self.client.chat.completions.create(**request_kwargs)
            return response.choices[0].message.content
        except Exception as e:
            raise Exception(f'DeepSeek API调用失败: {str(e)}')

    def embeddings(self, text: str) -> List[float]:
        """获取文本嵌入"""
        return []