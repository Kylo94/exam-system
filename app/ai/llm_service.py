"""LLM服务"""

import json
from typing import Any, Dict, List, Optional
from .base import BaseAIService
from .providers.deepseek import DeepSeekProvider
from .providers.deepseek_anthropic import DeepSeekAnthropicProvider
from .providers.openai import OpenAIProvider
from .providers.minimax import MiniMaxProvider


class LLMService(BaseAIService):
    """LLM服务类"""

    def __init__(self, provider: str = 'deepseek'):
        """初始化LLM服务

        Args:
            provider: AI提供商（deepseek/deepseek_anthropic/openai/minimax）
        """
        super().__init__(provider)
        self._provider_instance = None

    @property
    def provider_instance(self):
        """获取提供商实例（懒加载）"""
        if self._provider_instance is None:
            api_key = self.config.get('api_key')
            base_url = self.config.get('base_url')

            if not api_key:
                raise ValueError(f'{self.provider} API密钥未配置')

            # 默认API地址
            DEFAULT_URLS = {
                'deepseek': 'https://api.deepseek.com',
                'deepseek_anthropic': 'https://api.deepseek.com/anthropic',
                'openai': 'https://api.openai.com/v1',
                'minimax': 'https://api.minimaxi.com/anthropic'
            }

            # 如果没有提供base_url，使用默认值
            if not base_url:
                base_url = DEFAULT_URLS.get(self.provider)

            if self.provider == 'deepseek':
                self._provider_instance = DeepSeekProvider(api_key, base_url)
            elif self.provider == 'deepseek_anthropic':
                self._provider_instance = DeepSeekAnthropicProvider(api_key, base_url)
            elif self.provider == 'openai':
                self._provider_instance = OpenAIProvider(api_key, base_url)
            elif self.provider == 'minimax':
                self._provider_instance = MiniMaxProvider(api_key, base_url)
            else:
                raise ValueError(f'不支持的AI提供商: {self.provider}')

        return self._provider_instance
    
    def generate_answer(self, question: str, context: Optional[str] = None) -> str:
        """生成答案
        
        Args:
            question: 问题文本
            context: 上下文信息（可选）
            
        Returns:
            生成的答案
        """
        messages = []
        
        # 添加系统提示
        system_prompt = "你是一个专业的答题助手，请根据问题提供准确、详细的答案。"
        messages.append({'role': 'system', 'content': system_prompt})
        
        # 添加上下文（如果有）
        if context:
            messages.append({
                'role': 'user',
                'content': f"背景信息：{context}\n\n问题：{question}"
            })
        else:
            messages.append({'role': 'user', 'content': question})
        
        try:
            return self.provider_instance.chat_completion(messages)
        except Exception as e:
            return f"生成答案时出错: {str(e)}"
    
    def grade_answer(self, question: str, user_answer: str, correct_answer: str) -> Dict[str, Any]:
        """批改答案
        
        Args:
            question: 问题文本
            user_answer: 用户答案
            correct_answer: 正确答案
            
        Returns:
            批改结果，包含分数和反馈
        """
        prompt = f"""
        请批改以下答案：
        
        问题：{question}
        
        正确答案：{correct_answer}
        
        用户答案：{user_answer}
        
        请按照以下格式返回JSON结果：
        {{
            "score": 0.0到1.0之间的分数,
            "feedback": "详细的批改反馈",
            "correctness": "正确/部分正确/错误",
            "suggestions": "改进建议"
        }}
        
        只返回JSON，不要有其他内容。
        """
        
        messages = [
            {'role': 'system', 'content': '你是一个专业的批改老师，请客观、公正地批改答案。'},
            {'role': 'user', 'content': prompt}
        ]
        
        try:
            response = self.provider_instance.chat_completion(messages)
            # 尝试解析JSON
            result = json.loads(response.strip())
            return result
        except json.JSONDecodeError:
            # 如果返回的不是JSON，创建默认结果
            return {
                'score': 0.5,
                'feedback': '无法解析AI批改结果',
                'correctness': '未知',
                'suggestions': '请检查答案格式'
            }
        except Exception as e:
            return {
                'score': 0.0,
                'feedback': f'批改过程中出错: {str(e)}',
                'correctness': '错误',
                'suggestions': '请稍后重试'
            }
    
    def generate_question(self, subject: str, level: str, question_type: str) -> Dict[str, Any]:
        """生成题目
        
        Args:
            subject: 科目
            level: 难度等级
            question_type: 题目类型
            
        Returns:
            生成的题目信息
        """
        prompt = f"""
        请生成一个{subject}科目的{level}难度{question_type}类型题目。
        
        请按照以下格式返回JSON结果：
        {{
            "content": "题目内容",
            "options": ["选项A", "选项B", "选项C", "选项D"]（如果是选择题）,
            "correct_answer": "正确答案",
            "explanation": "答案解析",
            "tags": ["标签1", "标签2"]
        }}
        
        如果是选择题，options字段为数组；如果是简答题，options字段为空数组。
        只返回JSON，不要有其他内容。
        """
        
        messages = [
            {'role': 'system', 'content': '你是一个专业的题目生成器，请生成高质量的教育题目。'},
            {'role': 'user', 'content': prompt}
        ]
        
        try:
            response = self.provider_instance.chat_completion(messages)
            result = json.loads(response.strip())
            
            # 确保必要字段存在
            if 'content' not in result:
                result['content'] = f'{subject}相关题目'
            if 'options' not in result:
                result['options'] = []
            if 'correct_answer' not in result:
                result['correct_answer'] = '参考答案'
            if 'explanation' not in result:
                result['explanation'] = '解析说明'
            if 'tags' not in result:
                result['tags'] = [subject, level, question_type]
            
            return result
        except json.JSONDecodeError:
            # 返回默认题目
            return {
                'content': f'请解释{subject}中的核心概念。',
                'options': [],
                'correct_answer': '参考答案内容',
                'explanation': '这是一个示例题目的解析。',
                'tags': [subject, level, question_type]
            }
        except Exception as e:
            return {
                'content': f'生成题目时出错: {str(e)}',
                'options': [],
                'correct_answer': '',
                'explanation': '',
                'tags': []
            }