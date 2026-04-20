"""MiniMax AI提供商 - 使用 Anthropic SDK"""

from typing import List
import anthropic
from . import BaseProvider


class MiniMaxProvider(BaseProvider):
    """MiniMax AI提供商 - 基于 Anthropic SDK"""

    def __init__(self, api_key: str, base_url: str = 'https://api.minimaxi.com/anthropic'):
        """初始化MiniMax提供商

        Args:
            api_key: MiniMax API密钥
            base_url: API基础URL
        """
        super().__init__(api_key, base_url)
        self._client = None

    @property
    def client(self):
        """获取 Anthropic 客户端"""
        if self._client is None:
            self._client = anthropic.Anthropic(
                api_key=self.api_key,
                base_url=self.base_url
            )
        return self._client

    def chat_completion(self, messages: list, **kwargs) -> str:
        """MiniMax聊天补全

        Args:
            messages: 消息列表，格式为 Anthropic 格式
            **kwargs: 其他参数

        Returns:
            模型回复

        Raises:
            Exception: API调用失败
        """
        model = kwargs.get('model', 'MiniMax-M2.7')
        temperature = kwargs.get('temperature', 0.7)
        max_tokens = kwargs.get('max_tokens', 2000)

        # 转换消息格式为 Anthropic 格式
        anthropic_messages = []
        system_message = ""

        for msg in messages:
            if msg.get('role') == 'system':
                system_message = msg.get('content', '')
            else:
                anthropic_messages.append({
                    "role": msg.get('role', 'user'),
                    "content": [
                        {
                            "type": "text",
                            "text": msg.get('content', '')
                        }
                    ]
                })

        try:
            message = self.client.messages.create(
                model=model,
                max_tokens=max_tokens,
                system=system_message if system_message else "You are a helpful assistant.",
                messages=anthropic_messages,
                temperature=temperature
            )

            # 提取回复内容（跳过思考块，只保留文本）
            text_result = []
            for block in message.content:
                if block.type == "text":
                    text_result.append(block.text)
                # 跳过 thinking block，不添加到结果中
                elif block.type == "thinking":
                    pass

            return "\n\n".join(text_result) if text_result else str(message.content)
        except Exception as e:
            raise Exception(f'MiniMax API调用失败: {str(e)}')

    def embeddings(self, text: str) -> List[float]:
        """获取文本嵌入（MiniMax不支持）"""
        return []