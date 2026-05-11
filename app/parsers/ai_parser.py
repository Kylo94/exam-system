"""AI 文档解析器"""
import logging
import re
from typing import Any, Dict, List, Optional

from .constants import TYPE_DISPLAY, VALID_QUESTION_TYPES
from .json_handler import JsonHandler

logger = logging.getLogger(__name__)


class AIParser:
    """AI 辅助的文档解析器（支持批量处理）"""

    MAX_TOKENS_CONFIG = {
        'default': 16000,
        'reasoning_model': 32000,  # R1等推理模型
        'deepseek_v4': 32000
    }

    SYSTEM_PROMPT = """你是一个专业的试题解析助手。你需要：
1. 检查每道题目的完整性，确保内容没有截断
2. 规范化选项格式（使用A、B、C、D作为选项ID）
3. 为每道题目补充答案解析（如果原文没有，请根据题目内容生成）
4. 如果题目有代码，保持代码的缩进格式不变
5. 保持原始题型不变，不要修改题目的类型
6. 返回标准化的JSON数组格式，每道题必须包含：type, content, options, correct_answer, points, explanation
7. **重要**：确保返回的JSON数组长度与输入题目数量一致，顺序保持一致
8. 为每道题提取3-5个标签（tags），必须严格遵守以下规则：
   - 标签只能是「知识点/技能点名称」，如：for循环、列表推导式、缩进规则、变量作用域
   - 绝对禁止使用以下内容作为标签：运算符（+、+=、==）、标点符号、文件后缀（.py）、软件名称（IDLE）、单个关键字（True、or、import、print）、单个内置函数名（input、int、type）、错误类型名（TypeError、IndentationError）
   - 不要提取过于基础的概念（如"变量"、"字符串"、"整数"），除非题目专门考察该概念
   - 每个标签2-6个汉字或英文单词，简洁精准"""

    def __init__(self, ai_config=None):
        self.ai_config = ai_config
        self.json_handler = JsonHandler()
        self._ai_service = None  # 懒加载

    def _get_ai_service(self):
        """懒加载AI服务实例"""
        if self._ai_service is None:
            from app.ai.llm_service import LLMService
            self._ai_service = LLMService(provider=self.ai_config.provider)
            self._ai_service.config = {
                'api_key': self.ai_config.api_key,
                'base_url': self.ai_config.base_url,
                'model': self.ai_config.model
            }
        return self._ai_service

    def parse(self, text: str, image_info: List[Dict] = None) -> List[Dict[str, Any]]:
        """使用 AI 从文本中解析试题（先规则解析再批量AI增强）"""
        if not self.ai_config:
            raise Exception("AI 配置未提供")

        from .rule_parser import RuleParser
        local_parser = RuleParser()
        local_questions = local_parser.parse(text, image_info or [])

        if not local_questions:
            logger.info("规则解析未提取到任何题目")
            return []

        return self.batch_enhance_questions(local_questions, image_info)

    def batch_enhance_questions(self, questions: List[Dict[str, Any]], image_info: List[Dict] = None) -> List[Dict[str, Any]]:
        """批量AI增强处理（一次API调用处理所有题目）"""
        if not self.ai_config:
            raise Exception("AI 配置未提供")
        if not questions:
            return []

        image_info = image_info or []
        prompt = self._build_batch_prompt(questions, image_info)

        messages = [
            {"role": "system", "content": self.SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ]

        max_tokens = self._calculate_max_tokens(self.ai_config.model)

        logger.info(f"===== AI 请求开始 =====")
        logger.info(f"题目数量: {len(questions)}")
        logger.info(f"System prompt: {messages[0]['content'][:500]}")
        logger.info(f"User prompt:\n{messages[1]['content'][:2000]}")
        logger.info(f"===== 发送给AI的消息 =====")

        try:
            ai_service = self._get_ai_service()
            response = ai_service.provider_instance.chat_completion(
                messages, max_tokens=max_tokens, temperature=0.3
            )
            logger.info(f"===== AI 响应 ({len(response)} 字符) =====")
            logger.info(f"AI响应内容:\n{response[:2000]}")

            enhanced = self.json_handler.parse_batch_response(response, len(questions))

            if not enhanced:
                logger.warning("AI响应解析失败，使用本地结果")
                return self._preserve_local_results(questions)

            return self._merge_local_and_ai_results(questions, enhanced, image_info)

        except Exception as e:
            logger.warning(f"批量增强失败: {e}", exc_info=True)
            return self._preserve_local_results(questions)

    def _calculate_max_tokens(self, model_name: str) -> int:
        """根据模型类型计算合适的max_tokens"""
        model_lower = model_name.lower()

        if 'reason' in model_lower or 'r1' in model_lower:
            return self.MAX_TOKENS_CONFIG['reasoning_model']
        elif 'deepseek-v4' in model_lower:
            return self.MAX_TOKENS_CONFIG['deepseek_v4']
        else:
            return self.MAX_TOKENS_CONFIG['default']

    def _build_batch_prompt(self, questions: List[Dict[str, Any]], image_info: List[Dict]) -> str:
        """构建批量处理的提示词"""
        images_by_question = self._organize_images(image_info)

        prompt_parts = [
            f"请解析以下 {len(questions)} 道题目，返回标准JSON数组（必须包含所有题目，保持顺序一致）。\n",
            "**要求**：",
            "1. type必须为以下之一：single_choice, multiple_choice, true_false, fill_blank, short_answer, coding",
            "2. 判断题（true_false）无选项（options设为[]），correct_answer为\"true\"或\"false\"",
            "3. 选择题（single_choice/multiple_choice）options必须是数组，每个选项为{\"id\":\"A\",\"text\":\"选项内容\"}格式",
            "4. 为每道题提取3-5个标签（tags），标签只能是知识点/技能点名称（如'for循环'、'列表推导式'），禁止使用：运算符(+、+=)、文件后缀(.py)、软件名(IDLE)、关键字(True、or)、内置函数名(input、print)、错误类型(TypeError)。每个标签2-6个汉字或英文单词，简洁精准",
            "5. 直接返回JSON数组，不要任何其他文字，不要用markdown包裹",
            "",
            "返回格式示例：",
            '[{"order":1,"type":"single_choice","content":"以下哪个是Python中用于遍历列表的循环语句？","options":[{"id":"A","text":"if"},{"id":"B","text":"for"},{"id":"C","text":"while"},{"id":"D","text":"def"}],"correct_answer":"B","tags":["for循环","列表遍历","迭代"],"explanation":"Python中for循环专门用于遍历可迭代对象"},{"order":2,"type":"true_false","content":"地球绕太阳公转一周约为365天","options":[],"correct_answer":"true","tags":["地球公转","年","天体运动"],"explanation":"地球公转周期约为365.25天"}]',
            "",
            "**题目列表**：",
            ""
        ]

        for idx, q in enumerate(questions):
            order_idx = idx + 1
            question_text = self._format_single_question(
                q, order_idx, images_by_question.get(order_idx, {})
            )
            prompt_parts.append(question_text)

        return "\n".join(prompt_parts)

    def _format_single_question(self, q: Dict, order_idx: int, images: Dict) -> str:
        """格式化单道题目的prompt"""
        q_type = q.get('type', 'single_choice')

        # 格式化选项
        options_text = self._format_options(q.get('options', []), images.get('option_images', {}))

        # 格式化图片信息
        img_text = self._format_image_info(images)

        type_display = TYPE_DISPLAY.get(q_type, '未知')

        return f"""题目{order_idx} [{type_display}]
题目内容：{q.get('content', '')}{img_text}
选项：{options_text if options_text else '(无选项，判断题为布尔判断)'}
"""

    def _format_options(self, options: List[Dict], option_images: Dict) -> str:
        """格式化选项文本"""
        if not options:
            return ""

        formatted = []
        for opt in options:
            opt_id = opt.get('id', '?')
            opt_text = opt.get('text', '')
            has_img = opt.get('has_image', False)
            opt_imgs = option_images.get(opt_id, [])
            opt_img_path = opt_imgs[0].get('image_path', '') if opt_imgs else ''
            img_marker = f" [图片: {opt_img_path}]" if has_img and opt_img_path else ""
            formatted.append(f"  - {opt_id}. {opt_text}{img_marker}")

        return "\n".join(formatted)

    def _format_image_info(self, images: Dict) -> str:
        """格式化图片信息"""
        parts = []

        if images.get('question_images'):
            paths = [img.get('image_path', '') for img in images['question_images'] if img.get('image_path')]
            if paths:
                parts.append(f"\n题目图片: {', '.join(paths)}")

        if images.get('option_images'):
            opt_imgs = []
            for k, v in images['option_images'].items():
                if v and v[0].get('image_path'):
                    opt_imgs.append(f"{k}->{v[0]['image_path']}")
            if opt_imgs:
                parts.append("\n选项图片: " + ", ".join(opt_imgs))

        return "".join(parts)

    def _merge_local_and_ai_results(self, local_questions: List[Dict], ai_results: List[Dict], image_info: List[Dict]) -> List[Dict[str, Any]]:
        """合并本地解析结果和AI增强结果"""
        # 构建AI结果的索引映射，提高查找效率
        ai_index_map = self._build_ai_result_index(ai_results)

        merged = []
        for idx, local_q in enumerate(local_questions):
            order = idx + 1
            ai_q = ai_index_map.get(order)

            result = self._merge_single_question(local_q, ai_q, order)
            merged.append(result)

        # 更新图片标记
        if image_info:
            merged = self._update_question_image_flags(merged, image_info)

        return merged

    def _build_ai_result_index(self, ai_results: List[Dict]) -> Dict[int, Dict]:
        """构建AI结果的索引映射"""
        index_map = {}
        for idx, r in enumerate(ai_results):
            # 尝试多种方式获取order
            order = r.get('order_index') or r.get('order') or idx + 1
            if isinstance(order, int):
                index_map[order] = r
        return index_map

    def _merge_single_question(self, local_q: Dict, ai_q: Optional[Dict], order: int) -> Dict:
        """合并单道题目的结果"""
        result = {**local_q}
        local_type = local_q.get('type', '')

        if ai_q and isinstance(ai_q, dict):
            # 特殊处理：判断题保留本地类型
            if local_type == 'true_false':
                result['type'] = 'true_false'
                result['options'] = []
            elif ai_q.get('type') in VALID_QUESTION_TYPES:
                result['type'] = ai_q.get('type')

            # 合并其他字段
            self._merge_field(result, ai_q, 'content')

            # 合并选项：用AI的选项（保留格式优化），但保留本地的图片信息
            if local_type != 'true_false' and ai_q.get('options'):
                local_option_images = self._extract_option_image_info(local_q.get('options', []))
                result['options'] = ai_q.get('options')
                self._restore_option_image_info(result['options'], local_option_images)
                logger.debug(f"题目{order} 选项合并: local={len(local_q.get('options', []))}项 "
                           f"(images={len(local_option_images)}), "
                           f"AI={len(ai_q.get('options', []))}项, "
                           f"result_sample={str(result['options'][:2])[:200]}")
            elif local_type == 'true_false':
                result['options'] = []
            elif 'options' not in result:
                result['options'] = local_q.get('options', [])

            self._merge_field(result, ai_q, 'correct_answer')
            self._merge_field_with_priority(result, local_q, ai_q, 'explanation')
            self._merge_field(result, ai_q, 'points')

            # 保留标签
            if ai_q.get('tags') is not None:
                result['tags'] = ai_q.get('tags')
                logger.debug(f"题目{order} AI返回标签: {ai_q['tags']}")

        # 保留本地的 question_metadata（AI不会返回这个，需要本地图片信息）
        if 'question_metadata' in local_q and local_q['question_metadata']:
            result['question_metadata'] = local_q['question_metadata']

        result['order_index'] = order
        return result

    @staticmethod
    def _extract_option_image_info(options: List[Dict]) -> Dict[str, Dict]:
        """从选项列表中提取图片信息"""
        if not options:
            return {}
        image_map = {}
        for opt in options:
            if isinstance(opt, dict) and opt.get('has_image') and opt.get('image_path'):
                image_map[opt.get('id', '')] = {
                    'has_image': True,
                    'image_path': opt.get('image_path')
                }
        return image_map

    @staticmethod
    def _restore_option_image_info(options: List[Dict], image_map: Dict[str, Dict]):
        """将图片信息恢复到选项列表中"""
        if not image_map or not options:
            return
        for opt in options:
            if isinstance(opt, dict) and opt.get('id') in image_map:
                opt['has_image'] = True
                opt['image_path'] = image_map[opt['id']]['image_path']

    def _merge_field(self, target: Dict, source: Dict, field: str):
        """合并单个字段"""
        if source.get(field):
            target[field] = source[field]

    def _merge_field_with_priority(self, target: Dict, local: Dict, ai: Dict, field: str):
        """优先使用本地字段，其次使用AI字段"""
        if local.get(field):
            target[field] = local[field]
        elif ai.get(field):
            target[field] = ai[field]

    def _preserve_local_results(self, questions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """保留本地解析结果（AI失败时调用）"""
        for idx, q in enumerate(questions):
            q['order_index'] = idx + 1
        return questions

    def _update_question_image_flags(self, questions: List[Dict[str, Any]], image_info: List[Dict]) -> List[Dict[str, Any]]:
        """根据实际的图片信息更新题目的图片标记"""
        images_by_question = self._organize_images(image_info)

        for question in questions:
            order_index = question.get('order_index', 0)
            if order_index not in images_by_question:
                continue

            q_images = images_by_question[order_index]
            self._update_question_images(question, q_images)

            if question.get('type') in ['single_choice', 'multiple_choice']:
                self._update_option_images(question, q_images)

        return questions

    def _organize_images(self, image_info: List[Dict]) -> Dict[int, Dict]:
        """按题目组织图片信息（存储完整图片字典）"""
        images_by_question = {}

        for img in image_info:
            q_num = img.get('question_number', 0) or 0
            if q_num <= 0:
                continue

            if q_num not in images_by_question:
                images_by_question[q_num] = {
                    'question_images': [],
                    'option_images': {}
                }

            if img.get('image_type') == 'question_image':
                images_by_question[q_num]['question_images'].append(img)
            elif img.get('image_type') == 'option_image':
                option_id = self._extract_option_id(img.get('text_context', ''))
                if option_id:
                    if option_id not in images_by_question[q_num]['option_images']:
                        images_by_question[q_num]['option_images'][option_id] = []
                    images_by_question[q_num]['option_images'][option_id].append(img)

        return images_by_question

    def _update_question_images(self, question: Dict, q_images: Dict):
        """更新题目图片"""
        question_images = q_images.get('question_images', [])
        if not question_images:
            return

        new_images = [img.get('image_path') for img in question_images if img.get('image_path')]
        if new_images:
            question['images'] = new_images
        question['content_has_image'] = len(new_images) > 0

    def _update_option_images(self, question: Dict, q_images: Dict):
        """更新选项图片"""
        option_images = q_images.get('option_images', {})
        if not option_images:
            return

        if 'question_metadata' not in question:
            question['question_metadata'] = {}

        if 'options_images' not in question['question_metadata']:
            question['question_metadata']['options_images'] = {}

        options_images_metadata = question['question_metadata']['options_images']

        for option in question.get('options', []):
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

    def _extract_option_id(self, text: str) -> Optional[str]:
        """从文本中提取选项ID（支持A-Z）"""
        if not text:
            return None

        text = text.strip()
        # 扩展支持A-Z和a-z
        patterns = [
            r'^([A-Z])[\.、]\s*',
            r'^\(([A-Z])\)\s*',
            r'^([A-Z])\s+',
            r'^([A-Za-z])[\.、）)\s]',  # 更宽松的匹配
        ]

        for pattern in patterns:
            match = re.match(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).upper()

        return None