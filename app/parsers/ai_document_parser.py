"""AI辅助文档解析服务"""

import re
import json
from typing import Dict, List, Any, Optional
from pathlib import Path

from app.services.ai_service import get_ai_service


class AIDocumentParser:
    """AI辅助的文档解析器"""

    def __init__(self, use_ai: bool = True):
        """
        初始化解析器

        Args:
            use_ai: 是否使用AI解析，默认True
        """
        self.use_ai = use_ai
        self.ai_service = None

    def parse_document(self, file_path: str) -> Dict[str, Any]:
        """
        解析文档，优先使用AI

        Args:
            file_path: 文档路径

        Returns:
            解析结果字典
        """
        # 1. 首先使用规则解析提取文本
        text = self._extract_text_from_docx(file_path)

        # 2. 使用AI解析试题
        if self.use_ai:
            questions = self._parse_with_ai(text)
        else:
            questions = self._parse_with_rules(text)

        # 3. 返回结果
        return {
            'success': True,
            'questions': questions,
            'question_count': len(questions),
            'raw_text': text,
            'parse_method': 'ai' if self.use_ai else 'rules'
        }

    def _extract_text_from_docx(self, file_path: str) -> str:
        """从Word文档提取文本"""
        try:
            from docx import Document
            doc = Document(file_path)

            paragraphs = []
            for para in doc.paragraphs:
                if para.text.strip():
                    paragraphs.append(para.text.strip())

            # 也提取表格内容
            for table in doc.tables:
                for row in table.rows:
                    for cell in row.cells:
                        if cell.text.strip():
                            paragraphs.append(cell.text.strip())

            return '\n'.join(paragraphs)
        except ImportError:
            raise Exception("需要安装 python-docx: pip install python-docx")
        except Exception as e:
            raise Exception(f"提取Word文档失败: {str(e)}")

    def _parse_with_ai(self, text: str) -> List[Dict[str, Any]]:
        """
        使用AI从文本中解析试题

        Args:
            text: 文本内容

        Returns:
            试题列表
        """
        try:
            # 获取AI服务
            ai_service = get_ai_service()

            # 构建提示词
            prompt = self._build_ai_prompt(text)

            # 调用AI
            messages = [
                {
                    "role": "system",
                    "content": "你是一个专业的试题解析助手，擅长从文档中提取各种类型的试题并转换为标准JSON格式。"
                },
                {"role": "user", "content": prompt}
            ]

            response = ai_service.chat(messages, max_tokens=4000, temperature=0.3)

            # 解析响应
            questions = self._parse_ai_response(response.get('content', ''))

            return questions

        except Exception as e:
            print(f"AI解析失败: {e}，回退到规则解析")
            # AI解析失败，回退到规则解析
            return self._parse_with_rules(text)

    def _parse_with_rules(self, text: str) -> List[Dict[str, Any]]:
        """
        使用规则从文本中解析试题

        Args:
            text: 文本内容

        Returns:
            试题列表
        """
        questions = []
        lines = text.split('\n')
        current_question = None
        question_number = 1
        current_section = None  # 当前题型部分
        current_options = []  # 当前问题的选项

        # 题型检测
        section_patterns = {
            'single_choice': [r'一、单选题|单选\(共'],
            'multiple_choice': [r'二、多选题|多选\(共'],
            'judgment': [r'三、判断题|判断\(共'],
            'fill_blank': [r'四、填空题|填空\(共'],
            'subjective': [r'五、简答题|简答\(共|编程题']
        }

        # 问题开始模式
        question_patterns = [
            r'^(\d+)\.\s*',  # 1.
            r'^(\d+)、\s*',  # 1、
        ]

        # 选项模式
        option_pattern = r'^([A-D])[\.、]\s*(.+)'

        # 答案和解析模式
        answer_pattern = r'正确答案[：:]\s*([A-D]+)'
        explanation_pattern = r'答案解析[：:]\s*'

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # 检测题型部分
            section_changed = False
            for q_type, patterns in section_patterns.items():
                for pattern in patterns:
                    if re.search(pattern, line):
                        current_section = q_type
                        section_changed = True
                        break
                if section_changed:
                    break

            if section_changed:
                continue

            # 检查是否是问题开始
            question_match = None
            for pattern in question_patterns:
                match = re.match(pattern, line)
                if match:
                    question_match = match
                    break

            if question_match:
                # 保存上一个问题
                if current_question:
                    # 添加之前收集的选项
                    current_question['options'] = current_options
                    questions.append(current_question)
                    current_options = []

                # 开始新问题
                # 移除题号
                content = re.sub(r'^(\d+)\.|^(\d+)、', '', line).strip()

                current_question = {
                    'type': current_section or 'single_choice',
                    'content': content,
                    'correct_answer': '',
                    'points': 2,  # 默认分值
                    'options': [],
                    'explanation': '',
                    'order_index': question_number
                }
                question_number += 1

            elif current_question:
                # 检查是否是选项
                option_match = re.match(option_pattern, line)
                if option_match and current_question['type'] in ['single_choice', 'multiple_choice']:
                    option_id = option_match.group(1)
                    option_text = option_match.group(2)
                    current_options.append({
                        'id': option_id,
                        'text': option_text
                    })
                else:
                    # 检查是否是答案
                    answer_match = re.search(answer_pattern, line)
                    if answer_match:
                        current_question['correct_answer'] = answer_match.group(1)
                    # 检查是否是解析
                    elif '答案解析' in line:
                        explanation_text = re.sub(explanation_pattern, '', line).strip()
                        if explanation_text:
                            current_question['explanation'] = explanation_text

        # 保存最后一个问题
        if current_question:
            current_question['options'] = current_options
            questions.append(current_question)

        return self._normalize_questions(questions)

    def _build_ai_prompt(self, text: str) -> str:
        """构建AI提示词"""
        prompt = f"""请从以下试卷文档中提取所有试题，并转换为JSON格式。

**要求：**
1. 识别所有题型：单选题(single_choice)、多选题(multiple_choice)、判断题(judgment)、填空题(fill_blank)、简答题(subjective)
2. 每道题必须包含以下字段：
   - type: 题型（single_choice/multiple_choice/judgment/fill_blank/subjective）
   - content: 题目内容（完整文本）
   - options: 选项列表（单选/多选题需要），格式为 [{"id": "A", "text": "..."}, ...]
   - correct_answer: 正确答案
   - points: 分值（根据题目难度自动判断，单选题2-5分，多选题3-5分，判断题1-2分，填空题2-3分，简答题5-10分）
   - explanation: 答案解析（从文档中提取）
   - order_index: 题号（按顺序从1开始）

3. 对于判断题：正确答案为"A"（正确）或"B"（错误）
4. 对于多选题：正确答案为多个字母组合，如"ABC"
5. 对于填空题和简答题：正确答案为文本内容

**试卷内容：**
{text[:5000]}

{text[5000:10000] if len(text) > 5000 else ''}

{text[10000:] if len(text) > 10000 else ''}

**重要：**
- 只返回JSON格式的试题数组
- 不要包含任何解释性文字
- 确保所有字段都完整
- 答案必须准确，从文档的"正确答案"或"答案解析"中提取"""

        return prompt

    def _parse_ai_response(self, response: str) -> List[Dict[str, Any]]:
        """
        解析AI响应，提取试题数组

        Args:
            response: AI响应文本

        Returns:
            试题列表
        """
        try:
            # 尝试找到JSON数组
            start_idx = response.find('[')
            end_idx = response.rfind(']') + 1

            if start_idx >= 0 and end_idx > start_idx:
                json_str = response[start_idx:end_idx]
                questions = json.loads(json_str)
            else:
                # 尝试直接解析
                questions = json.loads(response)

            # 验证和标准化试题
            return self._normalize_questions(questions)

        except json.JSONDecodeError as e:
            print(f"JSON解析失败: {e}")
            return []

    def _normalize_questions(self, questions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        标准化试题格式

        Args:
            questions: 原始试题列表

        Returns:
            标准化后的试题列表
        """
        normalized = []

        for idx, q in enumerate(questions):
            # 验证必需字段
            if not q.get('content'):
                continue

            # 标准化题型
            type_map = {
                '单选题': 'single_choice',
                '多选题': 'multiple_choice',
                '判断题': 'judgment',
                '填空题': 'fill_blank',
                '简答题': 'subjective',
                'single_choice': 'single_choice',
                'multiple_choice': 'multiple_choice',
                'true_false': 'judgment',
                'fill_blank': 'fill_blank',
                'short_answer': 'subjective'
            }
            q_type = q.get('type', 'single_choice')
            q_type = type_map.get(q_type, 'single_choice')

            # 标准化选项
            options = q.get('options', [])
            if q_type in ['single_choice', 'multiple_choice']:
                if isinstance(options, list):
                    # 确保选项格式正确
                    normalized_options = []
                    for opt in options:
                        if isinstance(opt, dict):
                            if 'id' not in opt:
                                opt['id'] = chr(65 + len(normalized_options))
                            if 'text' in opt:
                                normalized_options.append(opt)
                    options = normalized_options
                else:
                    options = []

            # 标准化答案
            correct_answer = q.get('correct_answer', '')
            if q_type == 'judgment':
                # 判断题答案标准化
                if correct_answer in ['正确', 'true', 'True', '是']:
                    correct_answer = 'A'
                elif correct_answer in ['错误', 'false', 'False', '否']:
                    correct_answer = 'B'

            normalized_q = {
                'type': q_type,
                'content': q['content'],
                'correct_answer': str(correct_answer),
                'points': int(q.get('points', 2)),
                'options': options,
                'explanation': q.get('explanation', ''),
                'order_index': idx + 1
            }

            normalized.append(normalized_q)

        return normalized

    def parse_to_exam(self, file_path: str, exam_title: str,
                     subject_id: int, level_id: int) -> Dict[str, Any]:
        """
        解析文档并转换为考试数据

        Args:
            file_path: 文档路径
            exam_title: 考试标题
            subject_id: 科目ID
            level_id: 等级ID

        Returns:
            考试数据字典
        """
        result = self.parse_document(file_path)

        questions = result.get('questions', [])
        total_points = sum(q['points'] for q in questions)

        return {
            'title': exam_title,
            'subject_id': subject_id,
            'level_id': level_id,
            'description': f"从文档 '{Path(file_path).name}' 导入",
            'duration_minutes': len(questions) * 2 if questions else 60,
            'total_points': total_points,
            'questions': questions,
            'parse_method': result.get('parse_method', 'ai'),
            'question_count': len(questions)
        }
