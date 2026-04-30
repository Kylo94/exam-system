"""AI 文档解析器"""

from typing import Dict, List, Any, Optional
from .json_handler import JsonHandler


class AIParser:
    """AI 辅助的文档解析器（支持批量处理）"""

    def __init__(self, ai_config=None):
        self.ai_config = ai_config
        self.json_handler = JsonHandler()

    def parse(self, text: str, image_info: List[Dict] = None) -> List[Dict[str, Any]]:
        """使用 AI 从文本中解析试题（先规则解析再批量AI增强）"""
        if not self.ai_config:
            raise Exception("AI 配置未提供")

        from .rule_parser import RuleParser
        local_parser = RuleParser()
        local_questions = local_parser.parse(text, image_info)

        if not local_questions:
            return []

        return self.batch_enhance_questions(local_questions, image_info)

    def batch_enhance_questions(self, questions: List[Dict[str, Any]], image_info: List[Dict] = None) -> List[Dict[str, Any]]:
        """批量AI增强处理（一次API调用处理所有题目）"""
        if not self.ai_config:
            raise Exception("AI 配置未提供")
        if not questions:
            return []

        from app.ai.llm_service import LLMService
        ai_service = LLMService(provider=self.ai_config.provider)
        ai_service.config = {
            'api_key': self.ai_config.api_key,
            'base_url': self.ai_config.base_url,
            'model': self.ai_config.model
        }

        prompt = self._build_batch_prompt(questions, image_info)

        messages = [
            {
                "role": "system",
                "content": """你是一个专业的试题解析助手。你需要：
1. 检查每道题目的完整性，确保内容没有截断
2. 规范化选项格式（使用A、B、C、D作为选项ID）
3. 为每道题目补充答案解析（如果原文没有，请根据题目内容生成）
4. 如果题目有代码，保持代码的缩进格式不变
5. 保持原始题型不变，不要修改题目的类型
6. 返回标准化的JSON数组格式，每道题必须包含：type, content, options, correct_answer, points, explanation
7. **重要**：确保返回的JSON数组长度与输入题目数量一致，顺序保持一致"""
            },
            {"role": "user", "content": prompt}
        ]

        model_name = self.ai_config.model
        if 'reason' in model_name.lower() or 'r1' in model_name.lower():
            max_tokens = 32000
        elif 'deepseek-v4' in model_name.lower():
            max_tokens = 32000
        else:
            max_tokens = 16000

        try:
            response = ai_service.provider_instance.chat_completion(
                messages, max_tokens=max_tokens, temperature=0.3
            )
            enhanced = self.json_handler.parse_batch_response(response, len(questions))

            if not enhanced:
                return self._preserve_local_results(questions)

            return self._merge_local_and_ai_results(questions, enhanced, image_info)

        except Exception as e:
            print(f"[AIParser] Batch enhance failed: {e}", flush=True)
            return self._preserve_local_results(questions)

    def _build_batch_prompt(self, questions: List[Dict[str, Any]], image_info: List[Dict] = None) -> str:
        """构建批量处理的提示词"""
        images_by_question = {}
        if image_info:
            for img in image_info:
                q_num = img.get('question_number', 0)
                if q_num not in images_by_question:
                    images_by_question[q_num] = {'question_images': [], 'option_images': {}}
                if img.get('image_type') == 'question_image':
                    images_by_question[q_num]['question_images'].append(img.get('image_path', ''))
                elif img.get('image_type') == 'option_image':
                    opt_id = self._extract_option_id(img.get('text_context', ''))
                    if opt_id:
                        if opt_id not in images_by_question[q_num]['option_images']:
                            images_by_question[q_num]['option_images'][opt_id] = []
                        images_by_question[q_num]['option_images'][opt_id].append(img.get('image_path', ''))

        type_display = {
            'single_choice': '单选题', 'multiple_choice': '多选题',
            'true_false': '判断题', 'fill_blank': '填空题',
            'short_answer': '简答题', 'coding': '编程题'
        }

        prompt = f"请解析以下 {len(questions)} 道题目，返回JSON数组（必须包含所有题目，保持顺序一致）：\n\n"

        for idx, q in enumerate(questions):
            q_type = q.get('type', 'single_choice')
            order_idx = idx + 1
            q_images = images_by_question.get(order_idx, {}).get('question_images', [])
            q_option_images = images_by_question.get(order_idx, {}).get('option_images', {})

            options_text = ""
            if isinstance(q.get('options'), list):
                for opt in q.get('options', []):
                    opt_id = opt.get('id', '?')
                    opt_text = opt.get('text', '')
                    has_img = opt.get('has_image', False)
                    opt_img_path = q_option_images.get(opt_id, [None])[0] if opt_id in q_option_images else None
                    img_marker = f" [图片: {opt_img_path}]" if has_img and opt_img_path else ""
                    options_text += f"  - {opt_id}. {opt_text}{img_marker}\n"

            img_text = ""
            if q_images:
                img_text = f"\n题目图片: {', '.join(q_images)}"
            if q_option_images:
                img_text += "\n选项图片: " + ", ".join([f"{k}->{v[0]}" for k, v in q_option_images.items()])

            prompt += f"""**题目 {order_idx}** [{type_display.get(q_type, '未知')}]
题目内容：{q.get('content', '')}{img_text}

选项：
{options_text if options_text else '(无选项)'}

分值：{q.get('points', 2)}分
本地解析答案解析：{q.get('explanation', '') if q.get('explanation') else '(无)'}

"""

        prompt += """**要求**：
1. 检查每道题目内容是否完整，如果被截断请补全
2. 确保选项格式规范（使用A、B、C、D作为ID）
3. 为每道题补充答案解析（优先用原文，如果没有则AI生成）
4. 如果题目包含代码，保持代码的缩进格式不变
5. **重要**：题型必须与上述提供的一致，不要改变题型
6. 直接返回JSON数组格式，不要使用markdown代码块包裹
7. **重要**：确保返回的JSON数组长度与输入题目数量完全一致！

返回格式：
[
  {"order": 1, "type": "single_choice", "content": "完整题目内容", "options": [{"id": "A", "text": "选项A"}, ...], "correct_answer": "A", "points": 2, "explanation": "解析..."},
  {"order": 2, "type": "multiple_choice", ...},
  ...
]

只返回JSON数组，不要有任何其他文字。"""

        return prompt

    def _merge_local_and_ai_results(self, local_questions: List[Dict], ai_results: List[Dict], image_info: List[Dict]) -> List[Dict[str, Any]]:
        """合并本地解析结果和AI增强结果"""
        merged = []

        for idx, local_q in enumerate(local_questions):
            ai_q = None
            for r in ai_results:
                if r.get('order_index', r.get('order', 0)) == idx + 1:
                    ai_q = r
                    break
            if ai_q is None and len(ai_results) > idx:
                ai_q = ai_results[idx]

            result = {**local_q}

            if ai_q and isinstance(ai_q, dict):
                if ai_q.get('type'):
                    result['type'] = ai_q.get('type')
                if ai_q.get('content'):
                    result['content'] = ai_q.get('content')
                if ai_q.get('options'):
                    result['options'] = ai_q.get('options')
                if ai_q.get('correct_answer'):
                    result['correct_answer'] = ai_q.get('correct_answer')

                local_explanation = local_q.get('explanation', '')
                ai_explanation = ai_q.get('explanation', '')
                if local_explanation:
                    result['explanation'] = local_explanation
                elif ai_explanation:
                    result['explanation'] = ai_explanation

                if ai_q.get('points'):
                    result['points'] = ai_q.get('points')

            result['order_index'] = idx + 1
            merged.append(result)

        if image_info and merged:
            merged = self._update_question_image_flags(merged, image_info)

        return merged

    def _preserve_local_results(self, questions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """保留本地解析结果（AI失败时调用）"""
        preserved = []
        for idx, q in enumerate(questions):
            q['order_index'] = idx + 1
            preserved.append(q)
        return preserved

    def _update_question_image_flags(self, questions: List[Dict[str, Any]], image_info: List[Dict]) -> List[Dict[str, Any]]:
        """根据实际的图片信息更新题目的图片标记"""
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
                    new_images = [img.get('image_path') for img in question_images if img.get('image_path')]
                    if new_images:
                        question['images'] = new_images
                    question['content_has_image'] = len(new_images) > 0

                if question.get('type') in ['single_choice', 'multiple_choice'] and 'options' in question:
                    option_images = images_by_question[order_index]['option_images']
                    if 'question_metadata' not in question:
                        question['question_metadata'] = {'options_images': {}}
                    options_images_metadata = question['question_metadata'].get('options_images', {})

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
        import re
        text = text.strip()
        patterns = [
            r'^([A-D])[\.、]\s*', r'^\(([A-D])\)\s*', r'^([A-D])\s+',
        ]
        for pattern in patterns:
            match = re.match(pattern, text)
            if match:
                return match.group(1).upper()
        return None