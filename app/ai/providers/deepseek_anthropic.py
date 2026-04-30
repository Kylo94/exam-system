"""DeepSeek AI提供商 - 使用 Anthropic SDK"""

from typing import List
from anthropic import Anthropic
from . import BaseProvider


class DeepSeekAnthropicProvider(BaseProvider):
    """DeepSeek AI提供商 - 基于 Anthropic SDK

    使用 Anthropic API 格式访问 DeepSeek
    base_url: https://api.deepseek.com/anthropic
    """

    def __init__(self, api_key: str, base_url: str = 'https://api.deepseek.com/anthropic'):
        """初始化DeepSeek Anthropic提供商

        Args:
            api_key: DeepSeek API密钥
            base_url: Anthropic格式的API基础URL
        """
        super().__init__(api_key, base_url)
        self._client = None

    @property
    def client(self):
        """获取 Anthropic 客户端"""
        if self._client is None:
            self._client = Anthropic(
                api_key=self.api_key,
                base_url=self.base_url
            )
        return self._client

    def chat_completion(self, messages: list, **kwargs) -> str:
        """DeepSeek聊天补全（Anthropic格式）

        Args:
            messages: 消息列表，格式为anthropic格式
            **kwargs: 其他参数

        Returns:
            模型回复

        Raises:
            Exception: API调用失败
        """
        model = kwargs.get('model', 'deepseek-v4-pro')
        max_tokens = kwargs.get('max_tokens', 4000)
        temperature = kwargs.get('temperature', 0.3)
        system = kwargs.get('system')
        thinking = kwargs.get('thinking')

        # 转换OpenAI格式messages到Anthropic格式
        anthropic_messages = []
        anthropic_content = []

        for msg in messages:
            role = msg.get('role')
            content = msg.get('content', '')

            if role == 'system':
                system = content
            elif role == 'user':
                anthropic_content.append({
                    'type': 'text',
                    'text': content
                })
            elif role == 'assistant':
                anthropic_content.append({
                    'type': 'text',
                    'text': content
                })

        # 构建请求参数
        request_kwargs = {
            'model': model,
            'max_tokens': max_tokens,
            'messages': anthropic_content if anthropic_content else [{'type': 'text', 'text': ''}],
        }

        if system:
            request_kwargs['system'] = system

        if temperature:
            request_kwargs['temperature'] = temperature

        # 对于deepseek-v4-flash模型，支持thinking参数
        if 'deepseek-v4-flash' in model and thinking:
            request_kwargs['thinking'] = {'type': 'enabled'}

        try:
            response = self.client.messages.create(**request_kwargs)
            return response.content[0].text
        except Exception as e:
            raise Exception(f'DeepSeek Anthropic API调用失败: {str(e)}')

    def embeddings(self, text: str) -> List[float]:
        """获取文本嵌入"""
        return []
