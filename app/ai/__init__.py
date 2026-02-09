"""AI模块

提供AI相关功能，包括：
1. LLM集成（多提供商支持）
2. 智能批改
3. 答案生成
4. 题目生成
"""

from .base import BaseAIService
from .llm_service import LLMService
from .grader_service import GraderService
from .generator_service import GeneratorService
from .providers.deepseek import DeepSeekProvider
from .providers.openai import OpenAIProvider

__all__ = [
    'BaseAIService',
    'LLMService',
    'GraderService',
    'GeneratorService',
    'DeepSeekProvider',
    'OpenAIProvider'
]