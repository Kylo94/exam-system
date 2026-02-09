"""AI基础服务类"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, List, Union
from flask import current_app


class BaseAIService(ABC):
    """AI服务基类"""
    
    def __init__(self, provider: str = 'deepseek'):
        """初始化AI服务
        
        Args:
            provider: AI提供商（deepseek/openai）
        """
        self.provider = provider
        self.config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """加载配置"""
        config = {
            'deepseek': {
                'api_key': current_app.config.get('DEEPSEEK_API_KEY'),
                'base_url': current_app.config.get('DEEPSEEK_BASE_URL', 'https://api.deepseek.com')
            },
            'openai': {
                'api_key': current_app.config.get('OPENAI_API_KEY'),
                'base_url': current_app.config.get('OPENAI_BASE_URL', 'https://api.openai.com/v1')
            }
        }
        return config.get(self.provider, {})
    
    @abstractmethod
    def generate_answer(self, question: str, context: Optional[str] = None) -> str:
        """生成答案
        
        Args:
            question: 问题文本
            context: 上下文信息（可选）
            
        Returns:
            生成的答案
        """
        pass
    
    @abstractmethod
    def grade_answer(self, question: str, user_answer: str, correct_answer: str) -> Dict[str, Any]:
        """批改答案
        
        Args:
            question: 问题文本
            user_answer: 用户答案
            correct_answer: 正确答案
            
        Returns:
            批改结果，包含分数和反馈
        """
        pass
    
    @abstractmethod
    def generate_question(self, subject: str, level: str, question_type: str) -> Dict[str, Any]:
        """生成题目
        
        Args:
            subject: 科目
            level: 难度等级
            question_type: 题目类型
            
        Returns:
            生成的题目信息
        """
        pass
    
    def validate_config(self) -> bool:
        """验证配置是否有效
        
        Returns:
            配置是否有效
        """
        api_key = self.config.get('api_key')
        return bool(api_key and api_key.strip())