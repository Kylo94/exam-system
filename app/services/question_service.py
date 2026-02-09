"""问题服务模块"""

import json
from typing import List, Optional, Dict, Any, Union
from flask_sqlalchemy import SQLAlchemy

from app.models import Question, Exam
from .base import BaseService


class QuestionService(BaseService[Question]):
    """问题服务类"""
    
    def __init__(self, db: SQLAlchemy):
        """初始化问题服务"""
        super().__init__(Question, db)
    
    def get_by_exam_id(self, exam_id: int) -> List[Question]:
        """根据考试ID获取问题
        
        Args:
            exam_id: 考试ID
            
        Returns:
            问题列表
        """
        return Question.query.filter_by(exam_id=exam_id).order_by(Question.order_index).all()
    
    def get_by_type(self, exam_id: int, question_type: str) -> List[Question]:
        """根据考试ID和问题类型获取问题
        
        Args:
            exam_id: 考试ID
            question_type: 问题类型
            
        Returns:
            问题列表
        """
        return Question.query.filter_by(
            exam_id=exam_id, 
            type=question_type
        ).order_by(Question.order_index).all()
    
    def create_question(self, exam_id: int, content: str, question_type: str,
                       score: float = 1.0, options: Optional[Dict[str, Any]] = None,
                       correct_answer: Optional[Union[str, List[str]]] = None,
                       explanation: str = "", order_index: int = 0) -> Question:
        """创建新问题
        
        Args:
            exam_id: 考试ID
            content: 问题内容
            question_type: 问题类型
            score: 分值
            options: 选项（JSON格式）
            correct_answer: 正确答案
            explanation: 答案解析
            order_index: 排序索引
            
        Returns:
            创建的问题
            
        Raises:
            ValueError: 考试不存在或数据验证失败
        """
        # 验证考试存在
        exam = Exam.query.get(exam_id)
        if not exam:
            raise ValueError(f"考试ID {exam_id} 不存在")
        
        # 验证问题类型
        valid_types = ['single_choice', 'multiple_choice', 'true_false', 'fill_blank', 'short_answer']
        if question_type not in valid_types:
            raise ValueError(f"问题类型必须是: {', '.join(valid_types)}")
        
        # 验证分值
        if score <= 0:
            raise ValueError("分值必须大于0")
        
        # 处理选项
        options_data = options or {}
        if question_type in ['single_choice', 'multiple_choice']:
            if not options_data.get('choices'):
                raise ValueError(f"{question_type} 类型的问题必须提供选项")
            
            # 验证正确答案格式
            if correct_answer is not None:
                if question_type == 'single_choice' and not isinstance(correct_answer, str):
                    raise ValueError("单选题的正确答案必须是字符串")
                elif question_type == 'multiple_choice' and not isinstance(correct_answer, list):
                    raise ValueError("多选题的正确答案必须是列表")
        
        # 处理正确答案
        answer_data = None
        if correct_answer is not None:
            if isinstance(correct_answer, list):
                answer_data = json.dumps(correct_answer, ensure_ascii=False)
            else:
                answer_data = str(correct_answer)
        
        return self.create({
            'exam_id': exam_id,
            'content': content,
            'type': question_type,
            'score': score,
            'options': options_data,
            'correct_answer': answer_data,
            'explanation': explanation,
            'order_index': order_index
        })
    
    def create_single_choice(self, exam_id: int, content: str, 
                            choices: List[str], correct_choice: str,
                            score: float = 1.0, explanation: str = "",
                            order_index: int = 0) -> Question:
        """创建单选题
        
        Args:
            exam_id: 考试ID
            content: 问题内容
            choices: 选项列表
            correct_choice: 正确选项
            score: 分值
            explanation: 答案解析
            order_index: 排序索引
            
        Returns:
            创建的问题
        """
        options = {'choices': choices}
        return self.create_question(
            exam_id=exam_id,
            content=content,
            question_type='single_choice',
            score=score,
            options=options,
            correct_answer=correct_choice,
            explanation=explanation,
            order_index=order_index
        )
    
    def create_multiple_choice(self, exam_id: int, content: str,
                              choices: List[str], correct_choices: List[str],
                              score: float = 1.0, explanation: str = "",
                              order_index: int = 0) -> Question:
        """创建多选题
        
        Args:
            exam_id: 考试ID
            content: 问题内容
            choices: 选项列表
            correct_choices: 正确选项列表
            score: 分值
            explanation: 答案解析
            order_index: 排序索引
            
        Returns:
            创建的问题
        """
        options = {'choices': choices}
        return self.create_question(
            exam_id=exam_id,
            content=content,
            question_type='multiple_choice',
            score=score,
            options=options,
            correct_answer=correct_choices,
            explanation=explanation,
            order_index=order_index
        )
    
    def create_true_false(self, exam_id: int, content: str,
                         is_true: bool, score: float = 1.0,
                         explanation: str = "", order_index: int = 0) -> Question:
        """创建判断题
        
        Args:
            exam_id: 考试ID
            content: 问题内容
            is_true: 是否正确
            score: 分值
            explanation: 答案解析
            order_index: 排序索引
            
        Returns:
            创建的问题
        """
        return self.create_question(
            exam_id=exam_id,
            content=content,
            question_type='true_false',
            score=score,
            correct_answer=str(is_true).lower(),
            explanation=explanation,
            order_index=order_index
        )
    
    def create_fill_blank(self, exam_id: int, content: str,
                         correct_answer: str, score: float = 1.0,
                         explanation: str = "", order_index: int = 0) -> Question:
        """创建填空题
        
        Args:
            exam_id: 考试ID
            content: 问题内容（可以包含空白处标记，如"___"）
            correct_answer: 正确答案
            score: 分值
            explanation: 答案解析
            order_index: 排序索引
            
        Returns:
            创建的问题
        """
        return self.create_question(
            exam_id=exam_id,
            content=content,
            question_type='fill_blank',
            score=score,
            correct_answer=correct_answer,
            explanation=explanation,
            order_index=order_index
        )
    
    def create_short_answer(self, exam_id: int, content: str,
                           correct_answer: str, score: float = 1.0,
                           explanation: str = "", order_index: int = 0) -> Question:
        """创建简答题
        
        Args:
            exam_id: 考试ID
            content: 问题内容
            correct_answer: 参考答案
            score: 分值
            explanation: 答案解析
            order_index: 排序索引
            
        Returns:
            创建的问题
        """
        return self.create_question(
            exam_id=exam_id,
            content=content,
            question_type='short_answer',
            score=score,
            correct_answer=correct_answer,
            explanation=explanation,
            order_index=order_index
        )
    
    def update_question(self, id: int, **kwargs) -> Optional[Question]:
        """更新问题信息
        
        Args:
            id: 问题ID
            **kwargs: 更新字段
            
        Returns:
            更新后的问题或None
            
        Raises:
            ValueError: 数据验证失败
        """
        instance = self.get_by_id(id)
        if not instance:
            return None
        
        # 验证考试存在
        if 'exam_id' in kwargs:
            exam = Exam.query.get(kwargs['exam_id'])
            if not exam:
                raise ValueError(f"考试ID {kwargs['exam_id']} 不存在")
        
        # 验证问题类型
        if 'type' in kwargs:
            valid_types = ['single_choice', 'multiple_choice', 'true_false', 'fill_blank', 'short_answer']
            if kwargs['type'] not in valid_types:
                raise ValueError(f"问题类型必须是: {', '.join(valid_types)}")
        
        # 验证分值
        if 'score' in kwargs and kwargs['score'] <= 0:
            raise ValueError("分值必须大于0")
        
        # 处理选项更新
        if 'options' in kwargs and kwargs['options'] is not None:
            options = kwargs['options']
            if instance.type in ['single_choice', 'multiple_choice']:
                if not options.get('choices'):
                    raise ValueError(f"{instance.type} 类型的问题必须提供选项")
        
        # 处理正确答案更新
        if 'correct_answer' in kwargs and kwargs['correct_answer'] is not None:
            correct_answer = kwargs['correct_answer']
            if instance.type == 'single_choice' and not isinstance(correct_answer, str):
                raise ValueError("单选题的正确答案必须是字符串")
            elif instance.type == 'multiple_choice' and not isinstance(correct_answer, list):
                raise ValueError("多选题的正确答案必须是列表")
            
            # 转换为JSON字符串
            if isinstance(correct_answer, list):
                kwargs['correct_answer'] = json.dumps(correct_answer, ensure_ascii=False)
            else:
                kwargs['correct_answer'] = str(correct_answer)
        
        return self.update(id, kwargs)
    
    def search_questions(self, exam_id: Optional[int] = None,
                        content: Optional[str] = None,
                        question_type: Optional[str] = None,
                        skip: int = 0, limit: int = 100) -> List[Question]:
        """搜索问题
        
        Args:
            exam_id: 考试ID
            content: 问题内容（模糊搜索）
            question_type: 问题类型
            skip: 跳过的记录数
            limit: 返回的最大记录数
            
        Returns:
            问题列表
        """
        query = Question.query
        
        if exam_id is not None:
            query = query.filter_by(exam_id=exam_id)
        
        if content:
            query = query.filter(Question.content.ilike(f"%{content}%"))
        
        if question_type:
            query = query.filter_by(type=question_type)
        
        query = query.order_by(Question.order_index, Question.created_at)
        
        return query.offset(skip).limit(limit).all()
    
    def get_question_with_options(self, question_id: int) -> Dict[str, Any]:
        """获取问题及其选项信息
        
        Args:
            question_id: 问题ID
            
        Returns:
            问题详情字典
        """
        question = self.get_by_id(question_id)
        if not question:
            raise ValueError(f"问题ID {question_id} 不存在")
        
        result = {
            'id': question.id,
            'content': question.content,
            'type': question.type,
            'score': question.score,
            'options': question.options,
            'correct_answer': question.correct_answer,
            'explanation': question.explanation,
            'order_index': question.order_index,
            'created_at': question.created_at,
            'updated_at': question.updated_at,
            'exam_id': question.exam_id
        }
        
        # 解析正确答案
        if question.correct_answer:
            try:
                if question.type == 'multiple_choice':
                    result['correct_answer_parsed'] = json.loads(question.correct_answer)
                elif question.type == 'true_false':
                    result['correct_answer_parsed'] = question.correct_answer.lower() == 'true'
                else:
                    result['correct_answer_parsed'] = question.correct_answer
            except json.JSONDecodeError:
                result['correct_answer_parsed'] = question.correct_answer
        
        return result
    
    def validate_answer(self, question_id: int, user_answer: Union[str, List[str]]) -> Dict[str, Any]:
        """验证用户答案
        
        Args:
            question_id: 问题ID
            user_answer: 用户答案
            
        Returns:
            验证结果字典
        """
        question = self.get_by_id(question_id)
        if not question:
            return {'is_correct': False, 'score': 0, 'reason': '问题不存在'}
        
        if not question.correct_answer:
            return {'is_correct': False, 'score': 0, 'reason': '问题没有设置正确答案'}
        
        try:
            if question.type == 'single_choice':
                correct_answer = question.correct_answer
                is_correct = str(user_answer) == correct_answer
                score = question.score if is_correct else 0
            
            elif question.type == 'multiple_choice':
                correct_answers = json.loads(question.correct_answer)
                if not isinstance(user_answer, list):
                    user_answer = [user_answer] if user_answer else []
                
                # 检查答案是否完全匹配（顺序不重要）
                user_set = set(str(a) for a in user_answer)
                correct_set = set(str(a) for a in correct_answers)
                is_correct = user_set == correct_set
                score = question.score if is_correct else 0
            
            elif question.type == 'true_false':
                correct_answer = question.correct_answer.lower() == 'true'
                user_bool = str(user_answer).lower() == 'true'
                is_correct = user_bool == correct_answer
                score = question.score if is_correct else 0
            
            elif question.type in ['fill_blank', 'short_answer']:
                # 对于填空题和简答题，需要更复杂的评分逻辑
                # 这里暂时简单比较字符串
                correct_answer = question.correct_answer
                is_correct = str(user_answer).strip().lower() == correct_answer.strip().lower()
                score = question.score if is_correct else 0
            
            else:
                return {'is_correct': False, 'score': 0, 'reason': '不支持的问题类型'}
            
            return {
                'is_correct': is_correct,
                'score': score,
                'question_score': question.score,
                'question_type': question.type
            }
            
        except Exception as e:
            return {'is_correct': False, 'score': 0, 'reason': f'答案验证出错: {str(e)}'}