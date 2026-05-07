"""AI模块

提供AI相关功能，包括：
1. LLM集成（多提供商支持）
2. 智能批改
3. 答案生成
4. 题目生成
"""

from .base import BaseAIService
from .generator_service import GeneratorService
from .grader_service import GraderService
from .llm_service import LLMService
from .providers.base import BaseProvider
from .providers.deepseek import DeepSeekProvider
from .providers.deepseek_anthropic import DeepSeekAnthropicProvider
from .providers.openai import OpenAIProvider

__all__ = [
    'BaseAIService',
    'BaseProvider',
    'LLMService',
    'GraderService',
    'GeneratorService',
    'DeepSeekProvider',
    'DeepSeekAnthropicProvider',
    'OpenAIProvider'
]
