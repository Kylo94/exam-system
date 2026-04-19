"""
AI服务测试 - LLM服务测试（使用mock）
"""
import pytest
from unittest.mock import patch, MagicMock
import json

from app.ai.llm_service import LLMService


class TestLLMServiceInit:
    """LLM服务初始化测试"""

    def test_default_provider(self):
        """测试默认提供商"""
        service = LLMService()
        assert service.provider == 'deepseek'

    def test_custom_provider(self):
        """测试自定义提供商"""
        service = LLMService(provider='openai')
        assert service.provider == 'openai'


class TestLLMServiceGenerateAnswer:
    """生成答案测试"""

    @patch.object(LLMService, 'provider_instance', new_callable=lambda: MagicMock())
    def test_generate_answer_success(self, mock_provider):
        """测试成功生成答案"""
        service = LLMService()
        mock_provider.chat_completion.return_value = "Python是一种解释型语言。"

        result = service.generate_answer("Python是什么语言？")

        assert "解释型" in result or "Python" in result
        mock_provider.chat_completion.assert_called_once()

    @patch.object(LLMService, 'provider_instance', new_callable=lambda: MagicMock())
    def test_generate_answer_with_context(self, mock_provider):
        """测试带上下文的答案生成"""
        service = LLMService()
        mock_provider.chat_completion.return_value = "答案是B。"

        result = service.generate_answer("哪个是正确的？", context="题目：1+1=?")

        mock_provider.chat_completion.assert_called_once()
        calls = mock_provider.chat_completion.call_args[0][0]
        assert len(calls) == 2  # system + user


class TestLLMServiceGradeAnswer:
    """答案批改测试"""

    @patch.object(LLMService, 'provider_instance', new_callable=lambda: MagicMock())
    def test_grade_answer_valid_json(self, mock_provider):
        """测试有效JSON批改结果"""
        service = LLMService()
        mock_provider.chat_completion.return_value = json.dumps({
            'score': 0.8,
            'feedback': '答案基本正确',
            'correctness': '部分正确',
            'suggestions': '可以更详细一些'
        })

        result = service.grade_answer(
            question="什么是Python？",
            user_answer="Python是一种编程语言",
            correct_answer="Python是一种解释型高级编程语言"
        )

        assert result['score'] == 0.8
        assert result['correctness'] == '部分正确'

    @patch.object(LLMService, 'provider_instance', new_callable=lambda: MagicMock())
    def test_grade_answer_invalid_json(self, mock_provider):
        """测试无效JSON批改结果"""
        service = LLMService()
        mock_provider.chat_completion.return_value = "这不是JSON格式"

        result = service.grade_answer(
            question="什么是Python？",
            user_answer="Python是一种编程语言",
            correct_answer="Python是一种解释型高级编程语言"
        )

        assert result['score'] == 0.5
        assert result['correctness'] == '未知'


class TestLLMServiceGenerateQuestion:
    """题目生成测试"""

    @patch.object(LLMService, 'provider_instance', new_callable=lambda: MagicMock())
    def test_generate_question_valid_json(self, mock_provider):
        """测试有效JSON题目生成"""
        service = LLMService()
        mock_provider.chat_completion.return_value = json.dumps({
            'content': 'Python是什么？',
            'options': ['A. 猫', 'B. 编程语言', 'C. 饮料', 'D. 电影'],
            'correct_answer': 'B',
            'explanation': 'Python是一种编程语言',
            'tags': ['Python', '基础', '概念']
        })

        result = service.generate_question(
            subject='Python',
            level='简单',
            question_type='single_choice'
        )

        assert result['content'] == 'Python是什么？'
        assert len(result['options']) == 4
        assert result['correct_answer'] == 'B'

    @patch.object(LLMService, 'provider_instance', new_callable=lambda: MagicMock())
    def test_generate_question_invalid_json(self, mock_provider):
        """测试无效JSON题目生成"""
        service = LLMService()
        mock_provider.chat_completion.return_value = "这不是JSON"

        result = service.generate_question(
            subject='Python',
            level='简单',
            question_type='single_choice'
        )

        # 应该返回默认题目
        assert 'content' in result
        assert 'options' in result
        assert result['options'] == []

    @patch.object(LLMService, 'provider_instance', new_callable=lambda: MagicMock())
    def test_generate_question_missing_fields(self, mock_provider):
        """测试缺少字段的JSON"""
        service = LLMService()
        mock_provider.chat_completion.return_value = json.dumps({
            'content': '简答题：什么是Python？'
        })

        result = service.generate_question(
            subject='Python',
            level='简单',
            question_type='short_answer'
        )

        # 应该补全缺失字段
        assert 'content' in result
        assert 'options' in result
        assert 'correct_answer' in result
        assert 'explanation' in result
        assert 'tags' in result