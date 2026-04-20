"""AI 文档解析器"""

from typing import Dict, List, Any, Optional
from .json_handler import JsonHandler


class AIParser:
    """AI 辅助的文档解析器"""

    def __init__(self, ai_config=None):
        """
        初始化 AI 解析器

        Args:
            ai_config: AI 配置对象
        """
        self.ai_config = ai_config
        self.json_handler = JsonHandler()

    def parse(self, text: str, image_info: List[Dict] = None) -> List[Dict[str, Any]]:
        """
        使用 AI 从文本中解析试题

        Args:
            text: 文本内容
            image_info: 图片信息列表

        Returns:
            试题列表
        """
        if not self.ai_config:
            raise Exception("AI 配置未提供")

        # 获取 AI 服务
        from app.ai.llm_service import LLMService

        ai_service = LLMService(provider=self.ai_config.provider)
        ai_service.config = {
            'api_key': self.ai_config.api_key,
            'base_url': self.ai_config.base_url,
            'model': self.ai_config.model
        }

        # 构建提示词
        prompt = self._build_ai_prompt(text, image_info)

        # 准备消息
        messages = [
            {
                "role": "system",
                "content": "你是一个专业的试题解析助手，擅长从文档中提取各种类型的试题并转换为标准JSON格式。"
            },
            {"role": "user", "content": prompt}
        ]

        # 调用 AI 服务
        model_name = self.ai_config.model
        if 'reason' in model_name.lower() or 'r1' in model_name.lower():
            max_tokens = 64000
        else:
            max_tokens = 16000

        response = ai_service.provider_instance.chat_completion(
            messages,
            max_tokens=max_tokens,
            temperature=0.7
        )

        # 解析响应
        questions = self.json_handler.parse_json_response(response)

        # 根据实际图片信息更新题目的图片标记
        if image_info and questions:
            questions = self._update_question_image_flags(questions, image_info)

        return questions

    def _build_ai_prompt(self, text: str, image_info: List[Dict] = None) -> str:
        """构建 AI 提示词"""
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
   - type: 题型
   - content: 题目内容
   - options: 选项列表（单选/多选题需要）
   - correct_answer: 正确答案
   - points: 分值
   - explanation: 答案解析
   - knowledge_point: 考点
   - content_has_image: 是否包含图片
   - order_index: 题号

3. 判断题：正确答案为"true"或"false"
4. 多选题：正确答案为多个字母组合，如"ABC"
5. **返回格式必须是有效的JSON数组，不要包含markdown代码块标记**

**JSON格式示例：**
[
  {{
    "type": "single_choice",
    "content": "以下哪个是机器人?",
    "options": [
      {{"id": "A", "text": "汽车", "has_image": false}},
      {{"id": "B", "text": "人", "has_image": false}}
    ],
    "correct_answer": "B",
    "points": 2,
    "explanation": "机器人是一种自动化机械。",
    "knowledge_point": "机器人基本概念",
    "content_has_image": false,
    "order_index": 1
  }}
]

**试卷内容（{len(text)}个字符）：**
{text}

**重要：**
- 只返回JSON格式的试题数组
- 不要包含任何解释性文字或markdown代码块标记
- 确保所有字段都完整
"""

        return prompt

    def _update_question_image_flags(self, questions: List[Dict[str, Any]], image_info: List[Dict]) -> List[Dict[str, Any]]:
        """根据实际的图片信息更新题目的图片标记"""
        import re
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
                    question['question_metadata'] = {
                        'options_images': {}
                    }

                if question.get('type') in ['single_choice', 'multiple_choice'] and 'options' in question:
                    option_images = images_by_question[order_index]['option_images']
                    if 'question_metadata' not in question:
                        question['question_metadata'] = {'options_images': {}}

                    for option in question['options']:
                        option_id = option.get('id', '')
                        if option_id in option_images and option_images[option_id]:
                            option['has_image'] = True
                            option['image_path'] = option_images[option_id][0].get('image_path')
                            question['question_metadata']['options_images'][option_id] = {
                                'has_image': True,
                                'image_path': option_images[option_id][0].get('image_path')
                            }

        return questions

    def _extract_option_id(self, text: str) -> Optional[str]:
        """从文本中提取选项ID"""
        if not text:
            return None
        import re
        text = text.strip()
        patterns = [
            r'^([A-D])[\.、]\s*',
            r'^\(([A-D])\)\s*',
            r'^([A-D])\s+',
        ]
        for pattern in patterns:
            match = re.match(pattern, text)
            if match:
                return match.group(1).upper()
        return None
