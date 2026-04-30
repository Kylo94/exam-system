"""JSON 处理和标准化模块"""

import re
import json
from typing import Dict, List, Any, Optional

try:
    import json5
    HAS_JSON5 = True
except ImportError:
    HAS_JSON5 = False


class JsonHandler:
    """JSON 处理和标准化"""

    def __init__(self):
        pass

    def parse_json_response(self, response: str) -> List[Dict[str, Any]]:
        """
        解析 AI 返回的 JSON 响应

        Args:
            response: AI 响应文本

        Returns:
            试题列表
        """
        # 预处理响应
        response = self._fix_json_format(response)

        # 尝试解析为 JSON 对象（{...}）
        stripped = response.strip()
        if stripped.startswith('{'):
            # 先尝试直接解析（处理 JSON 后面无额外内容的情况）
            try:
                data = json.loads(stripped)
                if 'type' in data or 'content' in data:
                    return [data]
            except json.JSONDecodeError:
                pass

            # 直接解析失败，尝试提取 JSON 对象部分
            json_str = self._extract_json_object(stripped)
            if json_str:
                try:
                    data = json.loads(json_str)
                    if 'type' in data or 'content' in data:
                        return [data]
                except json.JSONDecodeError:
                    pass

        # 尝试解析为 JSON 数组（[...]）
        if not stripped.startswith('[') or not stripped.endswith(']'):
            # 尝试找到 JSON 数组的位置
            json_start = stripped.find('[')
            if json_start >= 0:
                stripped = stripped[json_start:]

        # 尝试使用 json5 解析（更宽松）
        if HAS_JSON5:
            try:
                return self._normalize_questions(json5.loads(stripped))
            except Exception:
                pass

        # 回退到标准 JSON 解析
        try:
            return self._normalize_questions(json.loads(stripped))
        except json.JSONDecodeError as e:
            raise Exception(f"JSON解析失败: {str(e)}")

    def parse_batch_response(self, response: str, expected_count: int) -> List[Dict[str, Any]]:
        """解析批量AI返回的JSON响应，增强容错性"""
        response = self._fix_json_format(response)
        stripped = response.strip()

        # 移除markdown代码块
        if stripped.startswith('```'):
            stripped = re.sub(r'^```(?:json)?\s*', '', stripped)
            stripped = re.sub(r'\s*```$', '', stripped)

        # 尝试找到JSON数组开始位置
        if not stripped.startswith('['):
            json_start = stripped.find('[')
            if json_start >= 0:
                stripped = stripped[json_start:]

        # 尝试json5（更宽松）
        if HAS_JSON5:
            try:
                result = json5.loads(stripped)
                if isinstance(result, list):
                    return self._normalize_questions(result)
            except Exception:
                pass

        # 尝试标准JSON
        try:
            result = json.loads(stripped)
            if isinstance(result, list):
                return self._normalize_questions(result)
        except json.JSONDecodeError:
            pass

        # 如果JSON解析失败，尝试逐个提取题目
        extracted = self._extract_questions_from_text(stripped, expected_count)
        if extracted:
            return extracted

        return []

    def _extract_questions_from_text(self, text: str, expected_count: int) -> List[Dict[str, Any]]:
        """从文本中逐个提取题目（当JSON解析失败时的备用方案）"""
        results = []

        # 尝试用正则提取每个题目的JSON对象
        # 匹配 {"order": N, ...} 或 {"type": "...", ...}
        pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
        matches = re.findall(pattern, text)

        for match in matches:
            try:
                data = json.loads(match)
                if isinstance(data, dict) and ('content' in data or 'type' in data):
                    results.append(data)
            except json.JSONDecodeError:
                continue

        if results:
            return self._normalize_questions(results)
        return []

    def _fix_json_format(self, json_str: str) -> str:
        """
        修复 JSON 格式问题

        Args:
            json_str: 原始 JSON 字符串

        Returns:
            修复后的 JSON 字符串
        """
        # 移除 markdown 代码块标记
        json_str = re.sub(r'```json\s*', '', json_str)
        json_str = re.sub(r'```\s*', '', json_str)
        json_str = json_str.replace('```', '')

        # 移除控制字符
        json_str = ''.join(char for char in json_str if ord(char) >= 32 or char in ['\n', '\t'])

        # 移除开头和结尾的空白字符
        json_str = json_str.strip()

        return json_str

    def _extract_json_object(self, json_str: str) -> str:
        """提取 JSON 对象部分，正确处理嵌套括号"""
        if not json_str.startswith('{'):
            return None

        depth = 0
        in_string = False
        escape = False

        for i, char in enumerate(json_str):
            if escape:
                escape = False
                continue
            if char == '\\' and in_string:
                escape = True
                continue
            if char == '"' and not escape:
                in_string = not in_string
                continue
            if in_string:
                continue
            if char == '{':
                depth += 1
            elif char == '}':
                depth -= 1
                if depth == 0:
                    return json_str[:i+1]

        return None

    def _normalize_questions(self, questions: Any) -> List[Dict[str, Any]]:
        """
        标准化试题格式

        Args:
            questions: 原始试题数据

        Returns:
            标准化后的试题列表
        """
        if not isinstance(questions, list):
            return []

        normalized = []

        for idx, q in enumerate(questions):
            if not isinstance(q, dict) or not q.get('content'):
                continue

            # 标准化题型
            type_map = {
                '单选题': 'single_choice',
                '多选题': 'multiple_choice',
                '判断题': 'true_false',
                '填空题': 'fill_blank',
                '简答题': 'short_answer',
                'judgment': 'true_false',
                'subjective': 'short_answer',
                'judge': 'true_false',
                'true-false': 'true_false',
                'choice': 'single_choice',
                'multiple': 'multiple_choice',
            }
            q_type = q.get('type', 'single_choice')
            q_type = type_map.get(q_type, q_type) if isinstance(q_type, str) else 'single_choice'

            # 确保是有效类型
            valid_types = ['single_choice', 'multiple_choice', 'true_false', 'fill_blank', 'short_answer', 'coding']
            if q_type not in valid_types:
                q_type = 'single_choice'

            # 标准化选项
            options = q.get('options', [])
            if q_type in ['single_choice', 'multiple_choice']:
                if isinstance(options, list):
                    normalized_options = []
                    for opt in options:
                        if isinstance(opt, dict):
                            if 'id' not in opt:
                                opt['id'] = chr(65 + len(normalized_options))
                            normalized_options.append(opt)
                    options = normalized_options
                else:
                    options = []

            # 标准化答案
            correct_answer = str(q.get('correct_answer', ''))
            if q_type == 'true_false':
                if correct_answer in ['正确', 'true', 'True', '是', 'A']:
                    correct_answer = 'true'
                elif correct_answer in ['错误', 'false', 'False', '否', 'B']:
                    correct_answer = 'false'

            # 安全处理分值
            try:
                points = int(q.get('points', 2))
            except (ValueError, TypeError):
                points = 2

            normalized_q = {
                'type': q_type,
                'content': q['content'],
                'correct_answer': correct_answer,
                'points': points,
                'options': options,
                'explanation': q.get('explanation', ''),
                'knowledge_point': q.get('knowledge_point', ''),
                'order_index': idx + 1,
                'content_has_image': q.get('content_has_image', False),
                'image_path': q.get('image_path'),
                'question_metadata': q.get('question_metadata', {})
            }

            normalized.append(normalized_q)

        return normalized
