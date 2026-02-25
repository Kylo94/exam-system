"""AI辅助文档解析服务"""

import re
import json
from typing import Dict, List, Any, Optional
from pathlib import Path

from app.services.ai_service import get_ai_service


class AIDocumentParser:
    """AI辅助的文档解析器"""

    def __init__(self, use_ai: bool = True, progress_callback=None):
        """
        初始化解析器

        Args:
            use_ai: 是否使用AI解析，默认True
            progress_callback: 进度回调函数，接收 (percent, message) 参数
        """
        self.use_ai = use_ai
        self.ai_service = None
        self.log_messages = []  # 解析日志记录
        self.progress_callback = progress_callback  # 进度回调函数

    def _add_log(self, message: str, level: str = 'info', progress: int = None):
        """添加解析日志"""
        from datetime import datetime
        from flask import current_app

        timestamp = datetime.now().strftime('%H:%M:%S')
        icon = {'info': 'ℹ️', 'success': '✅', 'warning': '⚠️', 'error': '❌'}.get(level, '•')
        log_entry = f"[{timestamp}] {icon} {message}"
        self.log_messages.append(log_entry)
        print(log_entry)  # 输出到控制台

        # 如果有进度百分比，调用进度回调
        if progress is not None and self.progress_callback:
            self.progress_callback(progress, message)

        # 同时记录到 Flask 日志
        try:
            if level == 'success':
                current_app.logger.info(message)
            elif level == 'error':
                current_app.logger.error(message)
            elif level == 'warning':
                current_app.logger.warning(message)
            else:
                current_app.logger.debug(message)
        except RuntimeError:
            # 在应用上下文外时只打印
            pass

    def get_logs(self) -> str:
        """获取解析日志的HTML格式"""
        # 过滤掉包含堆栈信息的错误日志（包含"Traceback"或"File \"/"的内容）
        filtered_logs = []
        for log in self.log_messages:
            # 跳过包含详细错误信息的日志
            if 'Traceback' in log or 'File "/opt/' in log or 'File "/Users/' in log:
                continue
            # 跳过太长的错误详情行
            if '  File ' in log and 'line ' in log:
                continue
            filtered_logs.append(log)
        return '<br>'.join(filtered_logs)

    def parse_document(self, file_path: str) -> Dict[str, Any]:
        """
        解析文档，优先使用AI

        Args:
            file_path: 文档路径

        Returns:
            解析结果字典
        """
        self.log_messages = []  # 清空日志
        self._add_log(f"开始解析文档: {Path(file_path).name}", 'info', progress=5)

        # 1. 首先使用规则解析提取文本和图片信息
        self._add_log("步骤1: 从Word文档提取文本内容...", 'info', progress=10)
        text, image_info = self._extract_text_and_images_from_docx(file_path)
        self._add_log(f"✓ 文本提取完成，共 {len(text)} 个字符", 'success', progress=20)
        self._add_log(f"✓ 检测到 {len(image_info)} 张图片", 'success', progress=25)

        # 显示文本内容的前1000字符用于调试
        self._add_log(f"文本预览（前1000字符）:\n{text[:1000]}", 'info')

        for idx, img in enumerate(image_info):
            self._add_log(f"  图片{idx+1}: 位置{img['location']}, 对应题号{img['question_number']}, 类型:{img['image_type']}, 上下文: {img['text_context']}", 'info')

        # 2. 使用AI解析试题
        if self.use_ai:
            self._add_log("步骤2: 使用AI智能解析试题...", 'info', progress=30)
            self._add_log("  正在构建AI提示词...", 'info', progress=35)
            questions = self._parse_with_ai(text, image_info)
        else:
            self._add_log("步骤2: 使用规则解析试题...", 'info', progress=30)
            questions = self._parse_with_rules(text, image_info)

        # 3. 返回结果
        self._add_log(f"步骤3: 解析完成，共识别 {len(questions)} 道试题", 'success', progress=95)

        # 记录每道题的详细信息用于调试
        self._add_log("试题详细信息:", 'info')
        for idx, q in enumerate(questions, 1):
            q_type = q.get('type', 'unknown')
            q_content = q.get('content', '')[:100]  # 只显示前100字符
            q_has_image = q.get('content_has_image', False)
            self._add_log(f"  第{idx}题: 类型={q_type}, 包含图片={q_has_image}, 内容预览: {q_content}", 'info')

        self._add_log("解析成功完成！", 'success', progress=100)

        return {
            'success': True,
            'questions': questions,
            'question_count': len(questions),
            'raw_text': text,
            'parse_method': 'ai' if self.use_ai else 'rules',
            'parse_log': self.get_logs()
        }

    def _extract_text_and_images_from_docx(self, file_path: str) -> tuple:
        """从Word文档提取文本和图片信息"""
        try:
            from docx import Document
            from docx.shared import Inches
            doc = Document(file_path)

            paragraphs = []
            image_info = []
            current_question_number = None
            line_number = 0

            # 首先收集所有段落文本，用于查找上下文
            all_paragraphs_text = []
            for para in doc.paragraphs:
                all_paragraphs_text.append(para.text.strip())

            # 提取段落内容和图片
            for para_idx, para in enumerate(doc.paragraphs):
                line_number += 1
                if para.text.strip():
                    paragraphs.append(para.text.strip())

                    # 检测题号
                    match = re.match(r'^(\d+)[\.、]\s*', para.text.strip())
                    if match:
                        current_question_number = int(match.group(1))

                # 提取段落中的图片
                for run in para.runs:
                    for drawing in run._element.xpath('.//w:drawing'):
                        # 找到图片
                        pics = drawing.xpath('.//pic:pic')
                        if pics:
                            # 获取图片的上下文文本（前后段落）
                            context_text = self._get_image_context(all_paragraphs_text, para_idx, current_question_number)

                            # 判断图片是在题目中还是选项中
                            image_type = self._determine_image_type(context_text, current_question_number)

                            image_info.append({
                                'location': f'paragraph_{line_number}',
                                'question_number': current_question_number,
                                'image_type': image_type,
                                'text_context': context_text
                            })

            # 也提取表格内容
            table_line_number = line_number
            for table_idx, table in enumerate(doc.tables):
                for row_idx, row in enumerate(table.rows):
                    for cell_idx, cell in enumerate(row.cells):
                        if cell.text.strip():
                            paragraphs.append(cell.text.strip())
                            table_line_number += 1

                        # 检查单元格中的图片
                        for para in cell.paragraphs:
                            for run in para.runs:
                                for drawing in run._element.xpath('.//w:drawing'):
                                    pics = drawing.xpath('.//pic:pic')
                                    if pics:
                                        context_text = cell.text.strip()
                                        image_type = self._determine_image_type(context_text, current_question_number)
                                        image_info.append({
                                            'location': f'table_{table_idx}_row_{row_idx}_cell_{cell_idx}',
                                            'question_number': current_question_number,
                                            'image_type': image_type,
                                            'text_context': context_text
                                        })

            return '\n'.join(paragraphs), image_info

        except ImportError:
            raise Exception("需要安装 python-docx: pip install python-docx")
        except Exception as e:
            raise Exception(f"提取Word文档失败: {str(e)}")

    def _get_image_context(self, all_paragraphs: List[str], current_para_idx: int, current_question_number: int) -> str:
        """
        获取图片的上下文文本

        Args:
            all_paragraphs: 所有段落文本列表
            current_para_idx: 当前段落的索引
            current_question_number: 当前题号

        Returns:
            上下文文本
        """
        # 优先向后查找，找到第一个非空的段落
        for i in range(current_para_idx + 1, min(current_para_idx + 5, len(all_paragraphs))):
            if all_paragraphs[i].strip():
                return all_paragraphs[i][:100]

        # 如果向后找不到，向前查找
        for i in range(current_para_idx - 1, max(current_para_idx - 3, -1), -1):
            if all_paragraphs[i].strip():
                return all_paragraphs[i][:100]

        # 如果都找不到，返回当前题号
        if current_question_number:
            return f"第{current_question_number}题"

        return "未知上下文"

    def _determine_image_type(self, text: str, question_number: int) -> str:
        """判断图片类型（题目图片或选项图片）"""
        if not text:
            return 'unknown'

        text_lower = text.lower()
        # 如果文本包含 A、B、C、D 等选项标记，且格式类似选项，则认为是选项图片
        option_patterns = [
            r'^[A-D][\.、]\s*',
            r'^\([A-D]\)\s*',
            r'^[A-D]\s+',
            r'^\s*[A-D]\s*[、.]'
        ]

        for pattern in option_patterns:
            if re.match(pattern, text.strip()):
                return 'option_image'

        # 否则认为是题目图片
        return 'question_image'

    def _parse_with_ai(self, text: str, image_info: List[Dict] = None) -> List[Dict[str, Any]]:
        """
        使用AI从文本中解析试题

        Args:
            text: 文本内容

        Returns:
            试题列表
        """
        try:
            # 获取AI服务
            self._add_log("  正在获取AI服务...", 'info', progress=40)
            ai_service = get_ai_service()
            ai_provider = ai_service.__class__.__name__ if hasattr(ai_service, '__class__') else 'Unknown'
            model_name = getattr(ai_service, 'model', 'unknown')
            api_url = getattr(ai_service, 'api_url', '')
            # 提取域名显示
            if '://' in api_url:
                api_domain = api_url.split('://')[1].split('/')[0]
            else:
                api_domain = api_url
            self._add_log(f"  AI服务已就绪: {ai_provider} (模型: {model_name})", 'success', progress=45)
            self._add_log(f"  API地址: {api_domain}", 'info', progress=45)

            # 构建提示词
            self._add_log("  构建AI提示词...", 'info', progress=50)
            prompt = self._build_ai_prompt(text, image_info)
            self._add_log(f"  提示词长度: {len(prompt)} 字符", 'info', progress=55)

            # 调用AI
            self._add_log("  正在调用AI模型解析试题，这可能需要10-30秒...", 'info', progress=60)
            messages = [
                {
                    "role": "system",
                    "content": "你是一个专业的试题解析助手，擅长从文档中提取各种类型的试题并转换为标准JSON格式。"
                },
                {"role": "user", "content": prompt}
            ]

            response = ai_service.chat(messages, max_tokens=8000, temperature=0.3)
            response_content = response.get('content', '')
            self._add_log(f"  AI响应已收到，内容长度: {len(response_content)} 字符", 'success', progress=80)

            # 记录AI响应内容的前1000字符用于调试
            self._add_log(f"  AI响应预览（前1000字符）:\n{response_content[:1000]}", 'info')

            # 解析响应
            self._add_log("  解析AI返回的JSON数据...", 'info', progress=85)
            questions = self._parse_ai_response(response.get('content', ''))
            self._add_log(f"  成功解析 {len(questions)} 道试题", 'success', progress=90)

            # 根据实际图片信息更新题目的图片标记
            if image_info and questions:
                questions = self._update_question_image_flags(questions, image_info)
                self._add_log(f"  已根据实际图片信息更新题目图片标记", 'info')

            return questions

        except Exception as e:
            error_msg = f"AI解析失败: {str(e)}"
            self._add_log(error_msg, 'error')
            # 不显示完整堆栈，避免日志混乱
            # AI解析失败，回退到规则解析
            return self._parse_with_rules(text, image_info)

    def _parse_with_rules(self, text: str, image_info: List[Dict] = None) -> List[Dict[str, Any]]:
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
            'single_choice': [r'一、单选题'],
            'multiple_choice': [r'二、多选题'],
            'judgment': [r'[一二三]、判断题'],
            'fill_blank': [r'四、填空题'],
            'subjective': [r'五、简答题|编程题']
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
                    # 添加之前收集的选项（仅单选/多选题）
                    if current_question['type'] in ['single_choice', 'multiple_choice']:
                        current_question['options'] = current_options
                    questions.append(current_question)
                    current_options = []

                # 开始新问题
                # 移除题号
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
                    'points': 2,  # 默认分值
                    'options': [],
                    'explanation': '',
                    'order_index': question_number,
                    'content_has_image': has_image
                }
                question_number += 1

            elif current_question:
                # 检查是否是选项（仅单选/多选题）
                option_match = re.match(option_pattern, line)
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
                    answer_match = re.search(answer_pattern, line)
                    if answer_match:
                        current_question['correct_answer'] = answer_match.group(1)
                    # 检查是否是解析
                    elif '答案解析' in line:
                        explanation_text = re.sub(explanation_pattern, '', line).strip()
                        if explanation_text:
                            current_question['explanation'] = explanation_text
                    # 判断题特殊处理：答案格式为"正确答案：正确"或"正确答案：错误"
                    elif current_question['type'] == 'judgment' and '正确答案' in line:
                        answer_text = re.search(r'正确答案[：:]\s*(正确|错误)', line)
                        if answer_text:
                            current_question['correct_answer'] = answer_text.group(1)

        # 保存最后一个问题
        if current_question:
            # 添加之前收集的选项（仅单选/多选题）
            if current_question['type'] in ['single_choice', 'multiple_choice']:
                current_question['options'] = current_options
            questions.append(current_question)

        # 标准化试题格式
        normalized_questions = self._normalize_questions(questions)

        # 根据实际图片信息更新题目图片标记
        if image_info and normalized_questions:
            normalized_questions = self._update_question_image_flags(normalized_questions, image_info)

        return normalized_questions

    def _build_ai_prompt(self, text: str, image_info: List[Dict] = None) -> str:
        """构建AI提示词"""
        # 构建图片信息说明
        image_info_text = ""
        if image_info:
            image_info_text = "\n\n**图片信息：**\n"
            for idx, img in enumerate(image_info):
                img_type_cn = "题目图片" if img['image_type'] == 'question_image' else "选项图片"
                question_num = f"第{img['question_number']}题" if img['question_number'] else "未知题号"
                image_info_text += f"- 图片{idx+1}: {img_type_cn}, 位置: {img['location']}, 对应: {question_num}, 上下文: {img['text_context']}\n"

        prompt = f"""请从以下试卷文档中提取所有试题，并转换为JSON格式。{image_info_text}

**要求：**
1. 识别所有题型：单选题(single_choice)、多选题(multiple_choice)、判断题(true_false)、填空题(fill_blank)、简答题(short_answer)
2. 每道题必须包含以下字段：
   - type: 题型（single_choice/multiple_choice/true_false/fill_blank/short_answer）
   - content: 题目内容（完整文本）
   - options: 选项列表（单选/多选题需要），格式为 [{{"id": "A", "text": "...", "has_image": false}}, ...]
   - correct_answer: 正确答案
   - points: 分值（根据题目难度自动判断，单选题2-5分，多选题3-5分，判断题1-2分，填空题2-3分，简答题5-10分）
   - explanation: 答案解析（从文档中提取）
   - knowledge_point: 考点（分析题目涉及的知识点或考查内容）
   - content_has_image: 题目内容是否包含图片（true/false）
   - order_index: 题号（按顺序从1开始）

3. 对于判断题：正确答案为"true"（正确）或"false"（错误）
4. 对于多选题：正确答案为多个字母组合，如"ABC"
5. 对于填空题和简答题：正确答案为文本内容
6. 图片识别：
   - 如果题目内容中提到"如下图"、"如图所示"、"图片"等关键词，将content_has_image设为true
   - 如果选项中包含图片相关描述，将对应选项的has_image设为true
7. 考点分析：
   - 根据题目内容自动归纳考查的知识点
   - 例如："二叉树的遍历"、"动态规划"、"数组的查找"等

8. **代码题目特别处理（非常重要）：**
   - 题目或选项中如果包含代码（Python、Java、C++等），必须完整保留原始格式
   - 保持所有缩进（indentation）不变，特别是Python代码的缩进
   - 保持代码中的换行符和空格
   - 不要对代码进行格式化或自动修正
   - 如果代码使用制表符或空格缩进，保持原样
   - 代码块中的字符串、注释等内容也要完整保留
   - 示例：如果原文代码是4空格缩进，不要改成2空格或tab

**试卷内容：**
{text[:5000]}

{text[5000:10000] if len(text) > 5000 else ''}

{text[10000:] if len(text) > 10000 else ''}

**重要：**
- 只返回JSON格式的试题数组
- 不要包含任何解释性文字
- 确保所有字段都完整
- 答案必须准确，从文档的"正确答案"或"答案解析"中提取
- 考点要精炼准确，用简短的词组描述
- 代码题必须保持原始缩进和格式，这是最关键的要求"""

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

            self._add_log(f"  AI响应分析: 找到第一个 '[' 在位置 {start_idx}, 最后一个 ']' 在位置 {end_idx-1}", 'info')

            if start_idx >= 0 and end_idx > start_idx:
                json_str = response[start_idx:end_idx]
                self._add_log(f"  提取的JSON字符串长度: {len(json_str)} 字符", 'info')
                questions = json.loads(json_str)
                self._add_log(f"  JSON解析成功，获得 {len(questions) if isinstance(questions, list) else 1} 个对象", 'success')
            else:
                # 尝试直接解析
                self._add_log("  未找到JSON数组，尝试直接解析整个响应", 'warning')
                questions = json.loads(response)

            # 验证和标准化试题
            return self._normalize_questions(questions)

        except json.JSONDecodeError as e:
            error_msg = f"JSON解析失败: {str(e)}"
            self._add_log(error_msg, 'error')
            self._add_log(f"  AI响应内容（前500字符）: {response[:500]}", 'error')
            return []
        except Exception as e:
            error_msg = f"解析AI响应时发生异常: {str(e)}"
            self._add_log(error_msg, 'error')
            self._add_log(f"  AI响应内容（前500字符）: {response[:500]}", 'error')
            return []

    def _update_question_image_flags(self, questions: List[Dict[str, Any]], image_info: List[Dict]) -> List[Dict[str, Any]]:
        """
        根据实际的图片信息更新题目的图片标记

        Args:
            questions: 试题列表
            image_info: 图片信息列表

        Returns:
            更新后的试题列表
        """
        self._add_log(f"  开始根据实际图片信息更新题目标记，检测到 {len(image_info)} 个图片", 'info')

        for question in questions:
            order_index = question.get('order_index', 0)

            # 检查题目是否有图片
            has_question_image = False
            for img in image_info:
                if (img['question_number'] == order_index and
                    img['image_type'] == 'question_image'):
                    has_question_image = True
                    self._add_log(f"    第{order_index}题标记为包含题目图片", 'info')
                    break

            question['content_has_image'] = has_question_image

            # 检查选项是否有图片
            if question.get('type') in ['single_choice', 'multiple_choice'] and 'options' in question:
                for option in question['options']:
                    option_id = option.get('id', '')
                    has_option_image = False

                    for img in image_info:
                        if (img['question_number'] == order_index and
                            img['image_type'] == 'option_image' and
                            img['text_context'].strip().startswith(option_id)):
                            has_option_image = True
                            self._add_log(f"    第{order_index}题选项{option_id}标记为包含图片", 'info')
                            break

                    option['has_image'] = has_option_image

        return questions

    def _normalize_questions(self, questions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        标准化试题格式

        Args:
            questions: 原始试题列表

        Returns:
            标准化后的试题列表
        """
        normalized = []

        self._add_log(f"  标准化试题开始，原始题目数量: {len(questions)}", 'info')

        for idx, q in enumerate(questions):
            # 显示原始题目的所有字段和值
            self._add_log(f"  第{idx+1}题原始数据: {str(q)[:200]}", 'info')

            # 验证必需字段
            if not q.get('content'):
                self._add_log(f"  第{idx+1}题被过滤：缺少content字段，题目数据: {list(q.keys())}", 'warning')
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
            if q_type == 'true_false':
                # 判断题答案标准化为 true/false
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
                'order_index': idx + 1
            }

            normalized.append(normalized_q)

        self._add_log(f"  标准化完成，有效题目数量: {len(normalized)}", 'info')
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
