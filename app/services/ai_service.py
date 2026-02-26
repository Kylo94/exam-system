"""AI服务基类和实现"""

import requests
import json
from typing import Dict, List, Optional, Any
from abc import ABC, abstractmethod


class AIServiceBase(ABC):
    """AI服务基类"""

    def __init__(self, config):
        """
        初始化AI服务

        Args:
            config: AIConfig对象或配置字典
        """
        if hasattr(config, 'api_key'):
            self.api_key = config.api_key
            self.api_url = config.api_url
            self.model = config.model
            self.max_tokens = config.max_tokens
            self.temperature = config.temperature
            self.provider = config.provider
        else:
            self.api_key = config.get('api_key')
            self.api_url = config.get('api_url')
            self.model = config.get('model')
            self.max_tokens = config.get('max_tokens', 2000)
            self.temperature = config.get('temperature', 0.7)
            self.provider = config.get('provider', 'unknown')

    @abstractmethod
    def chat(self, messages: List[Dict], **kwargs) -> Dict[str, Any]:
        """
        聊天接口

        Args:
            messages: 消息列表，格式为 [{"role": "user", "content": "..."}]
            **kwargs: 其他参数

        Returns:
            响应结果，包含 'content', 'usage' 等字段
        """
        pass

    def extract_questions_from_text(self, text: str) -> List[Dict]:
        """
        从文本中提取试题

        Args:
            text: 文本内容

        Returns:
            试题列表
        """
        prompt = f"""请从以下文本中提取所有试题，并将其转换为JSON格式。

要求：
1. 支持以下题型：单选题(single_choice)、多选题(multiple_choice)、判断题(judgment)、填空题(fill_blank)、简答题(subjective)
2. 每道题包含以下字段：
   - type: 题型
   - content: 题目内容
   - options: 选项列表（单选/多选），格式为 [{"id": "A", "text": "..."}]
   - correct_answer: 正确答案
   - points: 分值（默认10分）
   - explanation: 题目解析（可选）
   - order_index: 题号

文本内容：
{text}

请只返回JSON格式的试题数组，不要包含其他说明文字。"""

        messages = [
            {"role": "system", "content": "你是一个专业的试题提取助手，擅长从文本中提取各种类型的试题并转换为JSON格式。"},
            {"role": "user", "content": prompt}
        ]

        response = self.chat(messages)

        try:
            # 提取JSON
            content = response.get('content', '')
            # 尝试查找JSON数组
            start_idx = content.find('[')
            end_idx = content.rfind(']') + 1
            if start_idx >= 0 and end_idx > start_idx:
                json_str = content[start_idx:end_idx]
                questions = json.loads(json_str)
                return questions
            else:
                # 尝试直接解析
                questions = json.loads(content)
                return questions
        except Exception as e:
            print(f"解析AI响应失败: {e}")
            return []

    def summarize_document(self, text: str) -> str:
        """
        文档摘要

        Args:
            text: 文本内容

        Returns:
            摘要内容
        """
        prompt = f"""请为以下文档内容生成一个简洁的摘要，包含以下要点：
1. 文档主题
2. 主要知识点
3. 适用难度等级

文本内容：
{text}"""

        messages = [
            {"role": "system", "content": "你是一个专业的文档摘要助手，擅长提取文档的核心内容。"},
            {"role": "user", "content": prompt}
        ]

        response = self.chat(messages)
        return response.get('content', '')


class DeepSeekService(AIServiceBase):
    """DeepSeek AI服务实现"""

    def __init__(self, config):
        super().__init__(config)

    def chat(self, messages: List[Dict], **kwargs) -> Dict[str, Any]:
        """
        DeepSeek聊天接口

        Args:
            messages: 消息列表
            **kwargs: 其他参数

        Returns:
            响应结果
        """
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.api_key}'
        }

        payload = {
            'model': self.model,
            'messages': messages,
            'max_tokens': kwargs.get('max_tokens', self.max_tokens),
            'temperature': kwargs.get('temperature', self.temperature),
        }

        # 增加超时时间到300秒（5分钟），推理模型需要更长的时间
        max_retries = 3
        timeout = 300  # 5分钟超时

        for attempt in range(max_retries):
            try:
                response = requests.post(
                    self.api_url,
                    headers=headers,
                    json=payload,
                    timeout=timeout
                )
                response.raise_for_status()

                data = response.json()

                # DeepSeek R1模型支持返回思考过程
                result = {
                    'content': data['choices'][0]['message']['content'],
                    'usage': data.get('usage', {}),
                    'model': data.get('model'),
                    'raw': data
                }

                # 如果有思考过程，提取出来（仅推理模型才有）
                message = data.get('choices', [{}])[0].get('message', {})

                # 方式1: 直接在message中有reasoning_content字段
                if 'reasoning_content' in message:
                    result['reasoning'] = message['reasoning_content']

                # 方式2: 在delta字段中有reasoning_content
                if 'delta' in message and 'reasoning_content' in message['delta']:
                    result['reasoning'] = message['delta']['reasoning_content']

                return result

            except requests.exceptions.Timeout as e:
                if attempt < max_retries - 1:
                    print(f"DeepSeek API请求超时，第{attempt + 1}次重试...")
                    continue
                raise Exception(f"DeepSeek API请求超时（已重试{max_retries}次）: {str(e)}")
            except requests.exceptions.HTTPError as e:
                # 捕获HTTP错误，返回详细错误信息
                error_msg = f"DeepSeek API返回HTTP错误: {str(e)}"
                try:
                    if hasattr(e, 'response') and hasattr(e.response, 'text'):
                        error_detail = e.response.text[:500]
                        error_msg += f"\nAPI响应: {error_detail}"
                except:
                    pass

                if attempt < max_retries - 1:
                    print(f"DeepSeek API请求失败，第{attempt + 1}次重试...")
                    import time
                    time.sleep(1)
                    continue
                raise Exception(error_msg)
            except requests.exceptions.RequestException as e:
                if attempt < max_retries - 1:
                    print(f"DeepSeek API请求失败，第{attempt + 1}次重试: {str(e)}")
                    import time
                    time.sleep(1)  # 等待1秒后重试
                    continue
                raise Exception(f"DeepSeek API请求失败（已重试{max_retries}次）: {str(e)}")
            except (KeyError, IndexError) as e:
                raise Exception(f"DeepSeek API响应格式错误: {str(e)}")


class OpenAIService(AIServiceBase):
    """OpenAI服务实现（预留）"""

    def __init__(self, config):
        super().__init__(config)

    def chat(self, messages: List[Dict], **kwargs) -> Dict[str, Any]:
        """
        OpenAI聊天接口

        Args:
            messages: 消息列表
            **kwargs: 其他参数

        Returns:
            响应结果
        """
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.api_key}'
        }

        payload = {
            'model': self.model,
            'messages': messages,
            'max_tokens': kwargs.get('max_tokens', self.max_tokens),
            'temperature': kwargs.get('temperature', self.temperature),
        }

        # 增加超时时间到300秒（5分钟），支持推理模型
        max_retries = 3
        timeout = 300  # 5分钟超时

        for attempt in range(max_retries):
            try:
                response = requests.post(
                    self.api_url,
                    headers=headers,
                    json=payload,
                    timeout=timeout
                )
                response.raise_for_status()

                data = response.json()

                return {
                    'content': data['choices'][0]['message']['content'],
                    'usage': data.get('usage', {}),
                    'model': data.get('model'),
                    'raw': data
                }

            except requests.exceptions.Timeout as e:
                if attempt < max_retries - 1:
                    print(f"OpenAI API请求超时，第{attempt + 1}次重试...")
                    continue
                raise Exception(f"OpenAI API请求超时（已重试{max_retries}次）: {str(e)}")
            except requests.exceptions.RequestException as e:
                if attempt < max_retries - 1:
                    print(f"OpenAI API请求失败，第{attempt + 1}次重试: {str(e)}")
                    import time
                    time.sleep(1)  # 等待1秒后重试
                    continue
                raise Exception(f"OpenAI API请求失败（已重试{max_retries}次）: {str(e)}")
            except (KeyError, IndexError) as e:
                raise Exception(f"OpenAI API响应格式错误: {str(e)}")


def get_ai_service(config=None) -> AIServiceBase:
    """
    根据配置获取对应的AI服务实例

    Args:
        config: AIConfig对象，如果为None则使用默认配置

    Returns:
        AI服务实例
    """
    if config is None:
        from app.models.ai_config import AIConfig
        config = AIConfig.get_active_provider()
        if not config:
            raise Exception("没有可用的AI配置")

    # 根据provider创建对应的服务
    provider_map = {
        'deepseek': DeepSeekService,
        'openai': OpenAIService,
    }

    service_class = provider_map.get(config.provider)
    if not service_class:
        raise Exception(f"不支持的AI提供商: {config.provider}")

    return service_class(config)
