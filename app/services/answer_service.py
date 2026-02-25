"""答案服务模块"""

from typing import List, Optional, Dict, Any
from flask_sqlalchemy import SQLAlchemy

from app.models import Answer, Submission, Question
from .base import BaseService


class AnswerService(BaseService[Answer]):
    """答案服务类"""
    
    def __init__(self, db: SQLAlchemy):
        """初始化答案服务"""
        super().__init__(Answer, db)
    
    def get_by_submission_id(self, submission_id: int) -> List[Answer]:
        """根据提交记录ID获取答案
        
        Args:
            submission_id: 提交记录ID
            
        Returns:
            答案列表
        """
        return Answer.query.filter_by(submission_id=submission_id).all()
    
    def get_by_question_id(self, question_id: int) -> List[Answer]:
        """根据问题ID获取答案
        
        Args:
            question_id: 问题ID
            
        Returns:
            答案列表
        """
        return Answer.query.filter_by(question_id=question_id).all()
    
    def get_user_answer(self, submission_id: int, question_id: int) -> Optional[Answer]:
        """获取用户对特定问题的答案
        
        Args:
            submission_id: 提交记录ID
            question_id: 问题ID
            
        Returns:
            答案或None
        """
        return Answer.query.filter_by(
            submission_id=submission_id,
            question_id=question_id
        ).first()
    
    def create_answer(self, submission_id: int, question_id: int,
                     user_answer: str, is_correct: bool = False,
                     score: float = 0.0) -> Answer:
        """创建新答案
        
        Args:
            submission_id: 提交记录ID
            question_id: 问题ID
            user_answer: 用户答案
            is_correct: 是否正确
            score: 得分
            
        Returns:
            创建的答案
            
        Raises:
            ValueError: 提交记录或问题不存在
        """
        # 验证提交记录存在
        submission = Submission.query.get(submission_id)
        if not submission:
            raise ValueError(f"提交记录ID {submission_id} 不存在")
        
        # 验证问题存在
        question = Question.query.get(question_id)
        if not question:
            raise ValueError(f"问题ID {question_id} 不存在")
        
        # 验证问题属于该考试
        if question.exam_id != submission.exam_id:
            raise ValueError("问题不属于该考试")
        
        return self.create({
            'submission_id': submission_id,
            'question_id': question_id,
            'user_answer': user_answer,
            'is_correct': is_correct,
            'score': score
        })
    
    def update_answer(self, id: int, **kwargs) -> Optional[Answer]:
        """更新答案信息
        
        Args:
            id: 答案ID
            **kwargs: 更新字段
            
        Returns:
            更新后的答案或None
        """
        instance = self.get_by_id(id)
        if not instance:
            return None
        
        # 验证提交记录存在
        if 'submission_id' in kwargs:
            submission = Submission.query.get(kwargs['submission_id'])
            if not submission:
                raise ValueError(f"提交记录ID {kwargs['submission_id']} 不存在")
        
        # 验证问题存在
        if 'question_id' in kwargs:
            question = Question.query.get(kwargs['question_id'])
            if not question:
                raise ValueError(f"问题ID {kwargs['question_id']} 不存在")
            
            # 验证问题属于该考试
            if 'submission_id' in kwargs:
                submission_id = kwargs['submission_id']
            else:
                submission_id = instance.submission_id
            
            submission = Submission.query.get(submission_id)
            if submission and question.exam_id != submission.exam_id:
                raise ValueError("问题不属于该考试")
        
        return self.update(id, kwargs)
    
    def search_answers(self, submission_id: Optional[int] = None,
                      question_id: Optional[int] = None,
                      is_correct: Optional[bool] = None,
                      skip: int = 0, limit: int = 100) -> List[Answer]:
        """搜索答案
        
        Args:
            submission_id: 提交记录ID
            question_id: 问题ID
            is_correct: 是否正确
            skip: 跳过的记录数
            limit: 返回的最大记录数
            
        Returns:
            答案列表
        """
        query = Answer.query
        
        if submission_id is not None:
            query = query.filter_by(submission_id=submission_id)
        
        if question_id is not None:
            query = query.filter_by(question_id=question_id)
        
        if is_correct is not None:
            query = query.filter_by(is_correct=is_correct)
        
        query = query.order_by(Answer.created_at)
        
        return query.offset(skip).limit(limit).all()
    
    def get_answer_statistics(self, question_id: int) -> Dict[str, Any]:
        """获取问题答案统计信息
        
        Args:
            question_id: 问题ID
            
        Returns:
            统计信息字典
        """
        # 获取所有答案
        answers = self.get_by_question_id(question_id)
        
        if not answers:
            return {
                'question_id': question_id,
                'total_answers': 0,
                'correct_count': 0,
                'incorrect_count': 0,
                'correct_rate': 0,
                'average_score': 0
            }
        
        total_answers = len(answers)
        correct_count = len([a for a in answers if a.is_correct])
        incorrect_count = total_answers - correct_count
        correct_rate = (correct_count / total_answers) * 100 if total_answers > 0 else 0

        # 平均得分（安全计算，跳过非数值类型的score）
        valid_scores = [a.score for a in answers if isinstance(a.score, (int, float))]
        total_score = sum(valid_scores)
        average_score = total_score / len(valid_scores) if len(valid_scores) > 0 else 0
        
        # 答案分布（对于选择题）
        answer_distribution = {}
        for answer in answers:
            answer_key = answer.user_answer
            answer_distribution[answer_key] = answer_distribution.get(answer_key, 0) + 1
        
        return {
            'question_id': question_id,
            'total_answers': total_answers,
            'correct_count': correct_count,
            'incorrect_count': incorrect_count,
            'correct_rate': round(correct_rate, 2),
            'average_score': round(average_score, 2),
            'answer_distribution': answer_distribution
        }
    
    def grade_answer(self, answer_id: int, is_correct: bool, score: float) -> Optional[Answer]:
        """评分答案
        
        Args:
            answer_id: 答案ID
            is_correct: 是否正确
            score: 得分
            
        Returns:
            更新后的答案或None
        """
        answer = self.get_by_id(answer_id)
        if not answer:
            return None
        
        # 获取问题
        question = Question.query.get(answer.question_id)
        if not question:
            return None
        
        # 验证分数不超过问题分值
        if score > question.score:
            score = question.score
        
        answer.is_correct = is_correct
        answer.score = score
        self.db.session.commit()
        
        # 更新提交记录的总分
        submission = Submission.query.get(answer.submission_id)
        if submission:
            # 重新计算总分
            submission_answers = self.get_by_submission_id(submission.id)
            submission.obtained_score = sum(a.score for a in submission_answers)
            
            # 计算百分比
            if submission.total_score > 0:
                submission.score_percentage = (submission.obtained_score / submission.total_score) * 100
            
            # 判断是否及格
            exam = Exam.query.get(submission.exam_id)
            if exam:
                submission.is_passed = submission.score_percentage >= exam.pass_score
            
            self.db.session.commit()
        
        return answer