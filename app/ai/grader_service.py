"""智能批改服务"""

import json
from typing import Any, Dict, List, Optional
from .llm_service import LLMService


class GraderService:
    """智能批改服务类"""
    
    def __init__(self, llm_service: Optional[LLMService] = None):
        """初始化批改服务
        
        Args:
            llm_service: LLM服务实例（如为None则创建默认实例）
        """
        self.llm_service = llm_service or LLMService()
    
    def grade_subjective_answer(self, question: Dict[str, Any], user_answer: str) -> Dict[str, Any]:
        """批改主观题答案
        
        Args:
            question: 问题信息
            user_answer: 用户答案
            
        Returns:
            批改结果
        """
        question_text = question.get('content', '')
        correct_answer = question.get('correct_answer', '')
        
        # 使用LLM批改
        result = self.llm_service.grade_answer(question_text, user_answer, correct_answer)
        
        # 添加额外信息
        result.update({
            'question_id': question.get('id'),
            'question_type': question.get('type', 'subjective'),
            'auto_graded': True,
            'grader': 'AI'
        })
        
        return result
    
    def grade_objective_answer(self, question: Dict[str, Any], user_answer: str) -> Dict[str, Any]:
        """批改客观题答案
        
        Args:
            question: 问题信息
            user_answer: 用户答案
            
        Returns:
            批改结果
        """
        correct_answer = question.get('correct_answer', '')
        options = question.get('options', [])
        
        # 对于选择题，直接比较答案
        if question.get('type') == 'multiple_choice':
            # 用户答案可能是选项索引或选项内容
            if isinstance(user_answer, str) and user_answer.isdigit():
                user_choice_index = int(user_answer)
                if 0 <= user_choice_index < len(options):
                    user_answer_text = options[user_choice_index]
                else:
                    user_answer_text = user_answer
            else:
                user_answer_text = user_answer
            
            # 正确答案可能是选项索引或选项内容
            if isinstance(correct_answer, str) and correct_answer.isdigit():
                correct_index = int(correct_answer)
                if 0 <= correct_index < len(options):
                    correct_answer_text = options[correct_index]
                else:
                    correct_answer_text = correct_answer
            else:
                correct_answer_text = correct_answer
            
            # 比较答案
            is_correct = str(user_answer_text).strip() == str(correct_answer_text).strip()
            score = 1.0 if is_correct else 0.0
            
            return {
                'score': score,
                'is_correct': is_correct,
                'correct_answer': correct_answer_text,
                'user_answer': user_answer_text,
                'feedback': '答案正确' if is_correct else '答案错误',
                'auto_graded': True,
                'grader': 'system'
            }
        
        # 对于判断题
        elif question.get('type') == 'true_false':
            is_correct = str(user_answer).strip().lower() == str(correct_answer).strip().lower()
            score = 1.0 if is_correct else 0.0
            
            return {
                'score': score,
                'is_correct': is_correct,
                'correct_answer': correct_answer,
                'user_answer': user_answer,
                'feedback': '判断正确' if is_correct else '判断错误',
                'auto_graded': True,
                'grader': 'system'
            }
        
        # 默认情况使用LLM批改
        else:
            return self.grade_subjective_answer(question, user_answer)
    
    def grade_exam_submission(self, submission: Dict[str, Any], answers: List[Dict[str, Any]]) -> Dict[str, Any]:
        """批改整个考试提交
        
        Args:
            submission: 提交信息
            answers: 答案列表
            
        Returns:
            批改结果汇总
        """
        total_score = 0.0
        max_score = 0.0
        graded_answers = []
        
        # 获取考试问题
        exam_id = submission.get('exam_id')
        # 这里需要从数据库获取问题，暂时假设questions已传入
        
        questions = submission.get('questions', [])
        
        for question in questions:
            # 查找对应的用户答案
            user_answer = None
            for answer in answers:
                if answer.get('question_id') == question.get('id'):
                    user_answer = answer.get('content', '')
                    break
            
            if user_answer is None:
                # 没有答案，得0分
                graded_answer = {
                    'question_id': question.get('id'),
                    'score': 0.0,
                    'feedback': '未作答',
                    'auto_graded': True
                }
            else:
                # 根据题型批改
                if question.get('type') in ['multiple_choice', 'true_false']:
                    graded_answer = self.grade_objective_answer(question, user_answer)
                else:
                    graded_answer = self.grade_subjective_answer(question, user_answer)
            
            # 计算分数
            question_score = graded_answer.get('score', 0.0)
            total_score += question_score
            max_score += 1.0  # 假设每题1分
            
            graded_answers.append(graded_answer)
        
        # 计算总分和百分比
        percentage = (total_score / max_score * 100) if max_score > 0 else 0
        
        return {
            'submission_id': submission.get('id'),
            'total_score': total_score,
            'max_score': max_score,
            'percentage': percentage,
            'graded_answers': graded_answers,
            'graded_at': '2024-01-01T00:00:00Z',  # 实际应使用当前时间
            'grader': 'AI'
        }