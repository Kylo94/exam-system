"""题目生成服务"""

import json
from typing import Any, Dict, List, Optional
from .llm_service import LLMService


class GeneratorService:
    """题目生成服务类"""
    
    def __init__(self, llm_service: Optional[LLMService] = None):
        """初始化生成服务
        
        Args:
            llm_service: LLM服务实例（如为None则创建默认实例）
        """
        self.llm_service = llm_service or LLMService()
    
    def generate_single_question(self, subject: str, level: str, question_type: str) -> Dict[str, Any]:
        """生成单个题目
        
        Args:
            subject: 科目
            level: 难度等级
            question_type: 题目类型
            
        Returns:
            生成的题目
        """
        return self.llm_service.generate_question(subject, level, question_type)
    
    def generate_question_bank(self, subject: str, levels: List[str], 
                              question_types: List[str], count_per_type: int = 5) -> List[Dict[str, Any]]:
        """生成题目库
        
        Args:
            subject: 科目
            levels: 难度等级列表
            question_types: 题目类型列表
            count_per_type: 每种类型生成的数量
            
        Returns:
            题目列表
        """
        questions = []
        
        for level in levels:
            for q_type in question_types:
                for _ in range(count_per_type):
                    question = self.generate_single_question(subject, level, q_type)
                    question['subject'] = subject
                    question['level'] = level
                    question['type'] = q_type
                    questions.append(question)
        
        return questions
    
    def generate_exam_paper(self, subject: str, level: str, question_count: int = 20) -> Dict[str, Any]:
        """生成试卷
        
        Args:
            subject: 科目
            level: 难度等级
            question_count: 题目数量
            
        Returns:
            试卷信息
        """
        # 定义题型分布
        question_type_distribution = {
            'multiple_choice': 0.4,  # 40%选择题
            'true_false': 0.2,       # 20%判断题
            'short_answer': 0.3,     # 30%简答题
            'essay': 0.1             # 10%论述题
        }
        
        questions = []
        current_index = 0
        
        for q_type, percentage in question_type_distribution.items():
            type_count = int(question_count * percentage)
            
            for _ in range(type_count):
                question = self.generate_single_question(subject, level, q_type)
                question['order_index'] = current_index
                question['score'] = 1.0  # 每题1分
                questions.append(question)
                current_index += 1
        
        # 如果因为取整少了题目，补充选择题
        while len(questions) < question_count:
            question = self.generate_single_question(subject, level, 'multiple_choice')
            question['order_index'] = current_index
            question['score'] = 1.0
            questions.append(question)
            current_index += 1
        
        # 计算总分
        total_score = sum(q.get('score', 1.0) for q in questions)
        
        return {
            'subject': subject,
            'level': level,
            'title': f'{subject} {level}难度模拟试卷',
            'description': f'自动生成的{subject}科目{level}难度模拟试卷，共{len(questions)}题',
            'total_score': total_score,
            'question_count': len(questions),
            'questions': questions,
            'estimated_time': len(questions) * 2,  # 预估时间（分钟）
            'generated_by': 'AI'
        }
    
    def generate_from_document(self, document_text: str, subject: str) -> List[Dict[str, Any]]:
        """从文档内容生成题目
        
        Args:
            document_text: 文档文本
            subject: 科目
            
        Returns:
            题目列表
        """
        prompt = f"""
        请根据以下文档内容生成5个相关的题目：
        
        文档内容：
        {document_text[:2000]}  # 限制长度
        
        科目：{subject}
        
        请按照以下格式返回JSON数组：
        [
          {{
            "content": "题目内容",
            "type": "题目类型",
            "correct_answer": "正确答案",
            "explanation": "答案解析",
            "level": "难度等级"
          }},
          ...
        ]
        
        题目类型可以是：multiple_choice（选择题）、true_false（判断题）、short_answer（简答题）
        难度等级可以是：easy（简单）、medium（中等）、hard（困难）
        
        只返回JSON，不要有其他内容。
        """
        
        messages = [
            {'role': 'system', 'content': '你是一个专业的题目生成器，请根据文档内容生成相关的教育题目。'},
            {'role': 'user', 'content': prompt}
        ]
        
        try:
            response = self.llm_service.provider_instance.chat_completion(messages)
            result = json.loads(response.strip())
            
            # 确保是列表
            if isinstance(result, dict):
                result = [result]
            
            # 添加科目信息
            for question in result:
                question['subject'] = subject
            
            return result
        except json.JSONDecodeError:
            # 返回示例题目
            return [
                {
                    'content': f'请总结{subject}的核心概念。',
                    'type': 'short_answer',
                    'correct_answer': '参考答案',
                    'explanation': '这是一个基于文档生成的示例题目。',
                    'level': 'medium',
                    'subject': subject
                }
            ]
        except Exception as e:
            return [
                {
                    'content': f'生成题目时出错: {str(e)}',
                    'type': 'short_answer',
                    'correct_answer': '',
                    'explanation': '',
                    'level': 'easy',
                    'subject': subject
                }
            ]