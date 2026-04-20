"""基于规则的题目解析器"""

import re
from typing import Dict, List, Any, Optional


class RuleParser:
    """基于规则的题目解析器"""

    # 题型检测模式
    SECTION_PATTERNS = {
        'single_choice': [r'一、单选题'],
        'multiple_choice': [r'二、多选题'],
        'judgment': [r'[一二三]、判断题'],
        'fill_blank': [r'四、填空题'],
        'subjective': [r'五、简答题|编程题']
    }

    # 问题开始模式
    QUESTION_PATTERNS = [
        r'^(\d+)\.\s*',  # 1.
        r'^(\d+)、\s*',  # 1、
    ]

    # 选项模式
    OPTION_PATTERN = r'^([A-D])[\.、]\s*(.+)'

    # 答案和解析模式
    ANSWER_PATTERN = r'正确答案[：:]\s*([A-D]+)'
    EXPLANATION_PATTERN = r'答案解析[：:]\s*'

    def __init__(self):
        """初始化规则解析器"""
        pass

    def parse(self, text: str, image_info: List[Dict] = None) -> List[Dict[str, Any]]:
        """
        使用规则从文本中解析试题

        Args:
            text: 文本内容
            image_info: 图片信息列表

        Returns:
            试题列表
        """
        questions = []
        lines = text.split('\n')
        current_question = None
        question_number = 1
        current_section = None
        current_options = []

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # 检测题型部分
            section_changed = False
            for q_type, patterns in self.SECTION_PATTERNS.items():
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
            for pattern in self.QUESTION_PATTERNS:
                match = re.match(pattern, line)
                if match:
                    question_match = match
                    break

            if question_match:
                # 保存上一个问题
                if current_question:
                    if current_question['type'] in ['single_choice', 'multiple_choice']:
                        current_question['options'] = current_options
                    questions.append(current_question)
                    current_options = []

                # 开始新问题
                content = re.sub(r'^(\d+)\.|^(\d+)、', '', line).strip()

                # 检查当前题目是否有图片
                has_image = False
                if image_info:
                    for img in image_info:
                        if img['question_number'] == question_number and img['image_type'] == 'question_image':
                            has_image = True
                            break

                current_question = {
                    'type': current_section or 'single_choice',
                    'content': content,
                    'correct_answer': '',
                    'points': 2,
                    'options': [],
                    'explanation': '',
                    'order_index': question_number,
                    'content_has_image': has_image
                }
                question_number += 1

            elif current_question:
                # 检查是否是选项
                option_match = re.match(self.OPTION_PATTERN, line)
                if option_match and current_question['type'] in ['single_choice', 'multiple_choice']:
                    option_id = option_match.group(1)
                    option_text = option_match.group(2)

                    # 检查选项是否有图片
                    has_image = False
                    if image_info:
                        for img in image_info:
                            if (img['question_number'] == current_question['order_index'] and
                                img['image_type'] == 'option_image' and
                                img['text_context'].strip().startswith(option_id)):
                                has_image = True
                                break

                    current_options.append({
                        'id': option_id,
                        'text': option_text,
                        'has_image': has_image
                    })
                else:
                    # 检查是否是答案
                    answer_match = re.search(self.ANSWER_PATTERN, line)
                    if answer_match:
                        current_question['correct_answer'] = answer_match.group(1)
                    # 检查是否是解析
                    elif '答案解析' in line:
                        explanation_text = re.sub(self.EXPLANATION_PATTERN, '', line).strip()
                        if explanation_text:
                            current_question['explanation'] = explanation_text
                    # 判断题特殊处理
                    elif current_question['type'] == 'judgment' and '正确答案' in line:
                        answer_text = re.search(r'正确答案[：:]\s*(正确|错误)', line)
                        if answer_text:
                            current_question['correct_answer'] = answer_text.group(1)

        # 保存最后一个问题
        if current_question:
            if current_question['type'] in ['single_choice', 'multiple_choice']:
                current_question['options'] = current_options
            questions.append(current_question)

        # 标准化
        return self._normalize_questions(questions, image_info)

    def _normalize_questions(self, questions: List[Dict[str, Any]], image_info: List[Dict] = None) -> List[Dict[str, Any]]:
        """标准化试题格式"""
        normalized = []

        for idx, q in enumerate(questions):
            if not q.get('content'):
                continue

            # 标准化题型
            type_map = {
                '单选题': 'single_choice',
                '多选题': 'multiple_choice',
                '判断题': 'true_false',
                '填空题': 'fill_blank',
                '简答题': 'short_answer',
                'single_choice': 'single_choice',
                'multiple_choice': 'multiple_choice',
                'judgment': 'true_false',
                'subjective': 'short_answer',
                'true_false': 'true_false',
                'fill_blank': 'fill_blank',
                'short_answer': 'short_answer'
            }
            q_type = q.get('type', 'single_choice')
            q_type = type_map.get(q_type, 'single_choice')

            # 标准化选项
            options = q.get('options', [])
            if q_type in ['single_choice', 'multiple_choice']:
                if isinstance(options, list):
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
                'correct_answer': str(correct_answer),
                'points': points,
                'options': options,
                'explanation': q.get('explanation', ''),
                'knowledge_point': q.get('knowledge_point', ''),
                'order_index': idx + 1
            }

            normalized.append(normalized_q)

        # 根据实际图片信息更新题目图片标记
        if image_info and normalized:
            normalized = self._update_question_image_flags(normalized, image_info)

        return normalized

    def _update_question_image_flags(self, questions: List[Dict[str, Any]], image_info: List[Dict]) -> List[Dict[str, Any]]:
        """根据实际的图片信息更新题目的图片标记"""
        # 按题号分组图片
        images_by_question = {}
        for img in image_info:
            q_num = img['question_number']
            if q_num not in images_by_question:
                images_by_question[q_num] = {'question_images': [], 'option_images': {}}
            if img['image_type'] == 'question_image':
                images_by_question[q_num]['question_images'].append(img)
            elif img['image_type'] == 'option_image':
                option_id = self._extract_option_id(img['text_context'])
                if option_id:
                    if option_id not in images_by_question[q_num]['option_images']:
                        images_by_question[q_num]['option_images'][option_id] = []
                    images_by_question[q_num]['option_images'][option_id].append(img)

        for question in questions:
            order_index = question.get('order_index', 0)

            if order_index in images_by_question:
                question_images = images_by_question[order_index]['question_images']
                if question_images:
                    question['content_has_image'] = True
                    question['image_path'] = question_images[0].get('image_path')

                if question.get('type') in ['single_choice', 'multiple_choice'] and 'options' in question:
                    option_images = images_by_question[order_index]['option_images']
                    for option in question['options']:
                        option_id = option.get('id', '')
                        if option_id in option_images and option_images[option_id]:
                            option['has_image'] = True
                            option['image_path'] = option_images[option_id][0].get('image_path')

        return questions

    def _extract_option_id(self, text: str) -> Optional[str]:
        """从文本中提取选项ID"""
        if not text:
            return None

        text = text.strip()
        patterns = [
            r'^([A-D])[\.、]\s*',
            r'^\(([A-D])\)\s*',
            r'^([A-D])\s+',
            r'^\s*选项\s*([A-D])',
            r'^\s*[A-D]\s*[、.]'
        ]

        for pattern in patterns:
            match = re.match(pattern, text)
            if match:
                return match.group(1).upper()

        return None
