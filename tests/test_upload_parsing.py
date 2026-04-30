"""测试上传解析流程"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock


class TestDeepSeekProvider:
    """测试 DeepSeek Provider"""

    def test_max_tokens_passed_correctly(self):
        """测试 max_tokens 参数正确传递"""
        from app.ai.providers.deepseek import DeepSeekProvider

        provider = DeepSeekProvider(api_key="test-key", base_url="https://api.deepseek.com")

        # 模拟 chat.completions.create 调用
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = '{"type": "single_choice", "content": "test"}'

        with patch.object(provider.client, 'chat') as mock_chat:
            mock_chat.completions.create = Mock(return_value=mock_response)

            result = provider.chat_completion(
                messages=[{"role": "user", "content": "test"}],
                max_tokens=4096
            )

            # 验证调用参数
            call_kwargs = mock_chat.completions.create.call_args[1]
            assert call_kwargs['max_tokens'] == 4096
            assert call_kwargs['model'] == 'deepseek-v4-pro'

    def test_large_max_tokens_not_truncated(self):
        """测试大 max_tokens 值不会导致响应被截断"""
        from app.ai.providers.deepseek import DeepSeekProvider

        provider = DeepSeekProvider(api_key="test-key", base_url="https://api.deepseek.com")

        # 模拟一个完整的 JSON 响应
        full_json = '{"type": "single_choice", "content": "test question", "options": [{"id": "A", "text": "opt"}], "correct_answer": "A", "points": 2, "explanation": "explanation"}'

        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = full_json

        with patch.object(provider.client, 'chat') as mock_chat:
            mock_chat.completions.create = Mock(return_value=mock_response)

            result = provider.chat_completion(
                messages=[{"role": "user", "content": "test"}],
                max_tokens=32000
            )

            # 验证返回完整内容
            assert len(result) == len(full_json)
            assert '"type": "single_choice"' in result


class TestJsonHandler:
    """测试 JSON 处理器"""

    def test_parse_object_format(self):
        """测试解析对象格式 {...}"""
        from app.parsers.json_handler import JsonHandler

        handler = JsonHandler()
        response = '{"type": "single_choice", "content": "test", "options": [], "correct_answer": "A"}'

        result = handler.parse_json_response(response)

        assert len(result) == 1
        assert result[0]['type'] == 'single_choice'
        assert result[0]['content'] == 'test'

    def test_parse_array_format(self):
        """测试解析数组格式 [...]"""
        from app.parsers.json_handler import JsonHandler

        handler = JsonHandler()
        response = '[{"type": "single_choice", "content": "test1"}, {"type": "single_choice", "content": "test2"}]'

        result = handler.parse_json_response(response)

        assert len(result) == 2
        assert result[0]['content'] == 'test1'
        assert result[1]['content'] == 'test2'

    def test_parse_incomplete_json_object(self):
        """测试解析不完整的 JSON 对象（被截断的情况）"""
        from app.parsers.json_handler import JsonHandler

        handler = JsonHandler()
        # 模拟 JSON 被截断
        truncated = '{"type": "single_choice", "content": "test'

        with pytest.raises(Exception) as exc_info:
            handler.parse_json_response(truncated)

        assert "JSON解析失败" in str(exc_info.value)

    def test_parse_json_with_markdown_code_block(self):
        """测试解析带 markdown 代码块的 JSON"""
        from app.parsers.json_handler import JsonHandler

        handler = JsonHandler()
        response = '''```json
{"type": "single_choice", "content": "test", "options": [], "correct_answer": "A"}
```'''

        result = handler.parse_json_response(response)

        assert len(result) == 1
        assert result[0]['type'] == 'single_choice'


class TestAIParser:
    """测试 AI 解析器"""

    def test_batch_enhance_questions_calls_llm(self):
        """测试 batch_enhance_questions 正确调用 LLM"""
        from app.parsers.ai_parser import AIParser
        from unittest.mock import MagicMock, patch

        ai_config = MagicMock()
        ai_config.model = 'deepseek-v4-pro'
        ai_config.provider = 'deepseek'
        ai_config.api_key = 'test-key'
        ai_config.base_url = 'https://api.deepseek.com'

        with patch('app.ai.llm_service.LLMService') as MockLLMService:
            mock_service_instance = MagicMock()
            mock_service_instance.provider_instance = MagicMock()
            mock_service_instance.provider_instance.chat_completion.return_value = '[{"order": 1, "type": "single_choice", "content": "test", "options": [{"id": "A", "text": "opt"}], "correct_answer": "A", "points": 2, "explanation": "test"}]'
            MockLLMService.return_value = mock_service_instance

            parser = AIParser(ai_config=ai_config)

            questions = [{
                'type': 'single_choice',
                'content': 'test question',
                'options': [{'id': 'A', 'text': 'opt'}],
                'correct_answer': 'A'
            }]

            result = parser.batch_enhance_questions(questions)

            # 验证调用发生
            mock_service_instance.provider_instance.chat_completion.assert_called_once()


class TestMaxTokensIntegration:
    """测试 max_tokens 集成"""

    def test_provider_receives_correct_max_tokens(self):
        """验证 Provider 收到正确的 max_tokens"""
        from app.ai.providers.deepseek import DeepSeekProvider

        provider = DeepSeekProvider(api_key="test-key")

        captured_kwargs = {}

        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = '{"test": true}'

        original_create = provider.client.chat.completions.create

        def capture_create(**kwargs):
            captured_kwargs.update(kwargs)
            return mock_response

        with patch.object(provider.client.chat.completions, 'create', side_effect=capture_create):
            provider.chat_completion(
                messages=[{"role": "user", "content": "test"}],
                max_tokens=16000,
                temperature=0.3
            )

        assert captured_kwargs['max_tokens'] == 16000
        assert captured_kwargs['temperature'] == 0.3


class TestTruncatedJsonScenarios:
    """测试 JSON 被截断的场景"""

    def test_truncated_json_object_raises_error(self):
        """测试被截断的 JSON 对象会抛出错误"""
        from app.parsers.json_handler import JsonHandler

        handler = JsonHandler()

        # 模拟被截断的 JSON - 结尾被截掉
        truncated = '{"type": "single_choice", "content": "test'

        with pytest.raises(Exception) as exc_info:
            handler.parse_json_response(truncated)

        assert "JSON解析失败" in str(exc_info.value)

    def test_truncated_json_with_missing_closing_braces(self):
        """测试缺少闭合括号的截断 JSON"""
        from app.parsers.json_handler import JsonHandler

        handler = JsonHandler()

        # 模拟缺少末尾的 JSON
        truncated = '{"type": "single_choice", "content": "test", "options": [{"id": "A'

        with pytest.raises(Exception) as exc_info:
            handler.parse_json_response(truncated)

        assert "JSON解析失败" in str(exc_info.value)

    def test_response_with_extra_data_after_json(self):
        """测试 JSON 后面有多余数据的情况 - 现在应该能正确处理"""
        from app.parsers.json_handler import JsonHandler

        handler = JsonHandler()

        # JSON 后面有多余字符 - 应该能成功提取并解析
        response = '{"type": "single_choice", "content": "test"}\nSome extra text'

        result = handler.parse_json_response(response)

        assert len(result) == 1
        assert result[0]['type'] == 'single_choice'
        assert result[0]['content'] == 'test'

    def test_deepseek_response_truncated_at_options(self):
        """模拟 DeepSeek 返回被截断在 options 中间的情况"""
        from app.parsers.json_handler import JsonHandler

        handler = JsonHandler()

        # 模拟 DeepSeek 返回的 JSON 在 options 中间被截断
        truncated = '''{
  "type": "single_choice",
  "content": "下列哪个函数可以将字符串转换为整数？（ ）",
  "options": [
    {"id": "A", "text": "str()"},
    {"id": "B", "text": "int()"},
    {"id": "C", "text": "float()"},
    {"id": "D", "text": "bool()"
  ],
  "correct_answer": "B",
  "points": 2'''

        with pytest.raises(Exception) as exc_info:
            handler.parse_json_response(truncated)

        assert "JSON解析失败" in str(exc_info.value)

    def test_deepseek_response_with_incomplete_explanation(self):
        """模拟 DeepSeek 返回的 explanation 被截断"""
        from app.parsers.json_handler import JsonHandler

        handler = JsonHandler()

        # 模拟 explanation 被截断
        truncated = '''{
  "type": "single_choice",
  "content": "test question",
  "options": [{"id": "A", "text": "opt"}],
  "correct_answer": "A",
  "points": 2,
  "explanation": "这是解释，但被截断了...
'''

        with pytest.raises(Exception):
            handler.parse_json_response(truncated)


class TestEndToEndParsing:
    """端到端解析测试"""

    @pytest.mark.asyncio
    async def test_full_parsing_flow(self):
        """测试完整解析流程"""
        from app.parsers.ai_parser import AIParser
        from unittest.mock import MagicMock, patch

        # 创建模拟的 AI 配置
        ai_config = MagicMock()
        ai_config.model = 'deepseek-v4-pro'
        ai_config.provider = 'deepseek'
        ai_config.api_key = 'test-key'
        ai_config.base_url = 'https://api.deepseek.com'

        with patch('app.ai.llm_service.LLMService') as MockLLMService:
            mock_service_instance = MagicMock()
            mock_service_instance.provider_instance = MagicMock()
            mock_service_instance.provider_instance.chat_completion.return_value = '''[{
                "order": 1,
                "type": "single_choice",
                "content": "下列哪个函数可以将字符串转换为整数？",
                "options": [
                    {"id": "A", "text": "str()"},
                    {"id": "B", "text": "int()"},
                    {"id": "C", "text": "float()"},
                    {"id": "D", "text": "bool()"}
                ],
                "correct_answer": "B",
                "points": 2,
                "explanation": "int() 函数用于将字符串转换为整数"
            }]'''
            MockLLMService.return_value = mock_service_instance

            parser = AIParser(ai_config=ai_config)

            questions = [{
                'type': 'single_choice',
                'content': '下列哪个函数可以将字符串转换为整数？',
                'options': [
                    {'id': 'A', 'text': 'str()'},
                    {'id': 'B', 'text': 'int()'},
                    {'id': 'C', 'text': 'float()'},
                    {'id': 'D', 'text': 'bool()'}
                ],
                'correct_answer': 'B',
                'order_index': 1
            }]

            result = parser.batch_enhance_questions(questions)

            # 验证结果
            assert result[0]['content'] == '下列哪个函数可以将字符串转换为整数？'
            assert result[0]['correct_answer'] == 'B'
            assert len(result[0]['options']) == 4


if __name__ == "__main__":
    pytest.main([__file__, "-v"])