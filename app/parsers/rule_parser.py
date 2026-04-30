"""基于规则的题目解析器"""

import re
from typing import Dict, List, Any, Optional, Tuple


class RuleParser:
    """基于规则的题目解析器"""

    # 题型检测模式
    SECTION_PATTERNS = {
        'single_choice': [r'一、单选题', r'单选题'],
        'multiple_choice': [r'二、多选题', r'多选题'],
        'judgment': [r'判断题'],
        'fill_blank': [r'填空题'],
        'subjective': [r'简答题', r'编程题', r'编程题\(python\)', r'编程题\(c\+\+\)']
    }

    # 问题开始模式
    QUESTION_PATTERNS = [
        r'^(\d+)[\.、]\s*(.+)',  # 1. 或 1、 格式
        r'^【(.+)】\s*(.+)',  # 【题目】格式
    ]

    # 选项模式
    OPTION_PATTERN = r'^([A-D])[\.、]\s*(.+)'

    # 答案和解析模式
    ANSWER_PATTERN = r'正确答案[：:]\s*([A-D]+|true|false|正确|错误)'
    EXPLANATION_PATTERNS = [
        r'答案解析[：:]\s*(.+)',
        r'解析[：:]\s*(.+)',
        r'【解析】\s*(.+)',
    ]

    def __init__(self):
        """初始化规则解析器"""
        pass

    def parse(self, text: str, image_info: List[Dict] = None) -> List[Dict[str, Any]]:
        """
        使用规则从文本中解析试题（增强版，支持代码缩进和多行内容）

        Args:
            text: 文本内容
            image_info: 图片信息列表

        Returns:
            试题列表
        """
        # 预处理：合并多行内容，处理代码块
        processed_text = self._preprocess_text(text)

        questions = []
        lines = processed_text.split('\n')
        current_question = None
        question_number = 0
        current_section = None
        current_options = []
        content_buffer = []  # 累积题目内容（处理多行）
        in_code_block = False
        code_indent = None

        for line in lines:
            original_line = line
            line_stripped = line.strip()

            # 跳过空行（但不是代码块内的空行）
            if not line_stripped and not in_code_block:
                continue

            # 检测题型部分
            section_changed = False
            for q_type, patterns in self.SECTION_PATTERNS.items():
                for pattern in patterns:
                    if re.search(pattern, line_stripped):
                        current_section = q_type
                        section_changed = True
                        break
                if section_changed:
                    break

            if section_changed:
                continue

            # 检查是否是问题开始
            question_match = None
            matched_pattern = None
            for pattern in self.QUESTION_PATTERNS:
                match = re.match(pattern, line_stripped)
                if match:
                    question_match = match
                    matched_pattern = pattern
                    break

            if question_match:
                # 保存上一个问题
                if current_question:
                    if content_buffer:
                        current_question['content'] = '\n'.join(content_buffer).strip()
                        content_buffer = []
                    if current_question['type'] in ['single_choice', 'multiple_choice']:
                        current_question['options'] = current_options
                    questions.append(current_question)
                    current_options = []

                # 开始新问题
                question_number += 1

                # 提取题目内容
                if matched_pattern == r'^(\d+)[\.、]\s*(.+)':
                    content = match.group(2).strip() if match.group(2) else ''
                else:
                    content = match.group(2).strip() if len(match.group.groups()) > 1 and match.group(2) else line_stripped

                content_buffer = [content] if content else []

                # 检查当前题目是否有图片
                has_image = False
                images = []
                if image_info:
                    for img in image_info:
                        if img['question_number'] == question_number and img['image_type'] == 'question_image':
                            has_image = True
                            images.append(img['image_path'])

                current_question = {
                    'type': current_section or 'single_choice',
                    'content': '',
                    'correct_answer': '',
                    'points': 2,
                    'options': [],
                    'explanation': '',
                    'order_index': question_number,
                    'content_has_image': has_image,
                    'images': images
                }
                current_section = None  # 重置章节，以便下题自动检测

            elif current_question:
                # 检查是否是选项
                option_match = re.match(self.OPTION_PATTERN, line_stripped)
                if option_match and current_question['type'] in ['single_choice', 'multiple_choice']:
                    # 遇到选项，说明题目内容已经结束，将buffer内容合并
                    if content_buffer:
                        current_question['content'] = '\n'.join(content_buffer).strip()
                        content_buffer = []

                    option_id = option_match.group(1)
                    option_text = option_match.group(2).strip()

                    # 检查选项是否有图片
                    has_image = False
                    image_path = None
                    if image_info:
                        for img in image_info:
                            if (img['question_number'] == current_question['order_index'] and
                                img['image_type'] == 'option_image' and
                                img['text_context'].strip().startswith(option_id)):
                                has_image = True
                                image_path = img['image_path']
                                break

                    current_options.append({
                        'id': option_id,
                        'text': option_text,
                        'has_image': has_image,
                        'image_path': image_path
                    })
                else:
                    # 非选项行，可能是：答案、解析、代码、继续的题目内容

                    # 检查是否是答案
                    answer_match = re.search(self.ANSWER_PATTERN, line_stripped)
                    if answer_match:
                        if content_buffer:
                            current_question['content'] = '\n'.join(content_buffer).strip()
                            content_buffer = []
                        current_question['correct_answer'] = answer_match.group(1).strip()
                        continue

                    # 检查是否是解析
                    is_explanation = False
                    for exp_pattern in self.EXPLANATION_PATTERNS:
                        exp_match = re.match(exp_pattern, line_stripped)
                        if exp_match:
                            if content_buffer:
                                current_question['content'] = '\n'.join(content_buffer).strip()
                                content_buffer = []
                            current_question['explanation'] = exp_match.group(1).strip()
                            is_explanation = True
                            break

                    if is_explanation:
                        continue

                    # 代码块处理
                    code_indicators = ['def ', 'class ', 'import ', 'for ', 'while ', 'if ', 'else:', 'elif ', 'print(',
                                      'int ', 'char ', 'float ', 'double ', 'void ', 'return ', '{', '}', '#include',
                                      'cout <<', 'cin >>', 'scanf', 'printf', 'public:', 'private:']

                    # 判断是否进入代码块
                    if not in_code_block:
                        # 检查是否是多行代码开始（以代码关键字开头或有明显缩进）
                        is_code_start = any(line_stripped.startswith(indicator) for indicator in code_indicators)

                        # 检查是否有缩进且不是选项（选项通常顶格或固定缩进）
                        indent = len(line) - len(line.lstrip())
                        is_indented = indent > 0
                        is_option = re.match(r'^[A-D][\.、)]', line_stripped)

                        if (is_code_start or (is_indented and not is_option and current_options)) and not answer_match:
                            # 这是代码行，添加到当前选项或内容
                            if current_options:
                                # 添加到最后一个选项
                                current_options[-1]['text'] += '\n' + line_stripped
                                continue
                            elif not answer_match and not is_explanation:
                                content_buffer.append(line_stripped)
                                continue

                    # 普通内容行，添加到内容buffer
                    if not answer_match and not is_explanation:
                        content_buffer.append(line_stripped)

        # 保存最后一个问题
        if current_question:
            if content_buffer:
                current_question['content'] = '\n'.join(content_buffer).strip()
            if current_question['type'] in ['single_choice', 'multiple_choice']:
                current_question['options'] = current_options
            questions.append(current_question)

        # 标准化
        return self._normalize_questions(questions, image_info)

    def _preprocess_text(self, text: str) -> str:
        """预处理文本，清理和规范化"""
        lines = text.split('\n')
        processed = []

        for line in lines:
            # 移除多余的空白但保留缩进结构
            # 如果行是代码相关，保持原始格式
            processed.append(line)

        return '\n'.join(processed)

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

            # 构建图片列表和选项图片元数据
            images = q.get('images', [])
            if images and not isinstance(images, list):
                images = [images]

            # 构建选项图片元数据
            options_images = {}
            for opt in options:
                if opt.get('has_image') and opt.get('image_path'):
                    options_images[opt['id']] = {
                        'has_image': True,
                        'image_path': opt['image_path']
                    }

            normalized_q = {
                'type': q_type,
                'content': q['content'],
                'correct_answer': str(correct_answer),
                'points': points,
                'options': options,
                'explanation': q.get('explanation', ''),
                'knowledge_point': q.get('knowledge_point', ''),
                'order_index': idx + 1,
                'images': images,
                'question_metadata': {
                    'options_images': options_images
                }
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
                    # 更新图片列表
                    new_images = [img.get('image_path') for img in question_images if img.get('image_path')]
                    if new_images:
                        question['images'] = new_images
                    question['content_has_image'] = len(new_images) > 0

                # 更新选项图片
                if question.get('type') in ['single_choice', 'multiple_choice'] and 'options' in question:
                    option_images = images_by_question[order_index]['option_images']
                    options_images_metadata = question.get('question_metadata', {}).get('options_images', {})

                    for option in question['options']:
                        option_id = option.get('id', '')
                        if option_id in option_images and option_images[option_id]:
                            img_info = option_images[option_id][0]
                            if img_info.get('image_path'):
                                option['has_image'] = True
                                option['image_path'] = img_info['image_path']
                                options_images_metadata[option_id] = {
                                    'has_image': True,
                                    'image_path': img_info['image_path']
                                }

                    question['question_metadata']['options_images'] = options_images_metadata

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
