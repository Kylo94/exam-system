"""考试提交服务模块"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from flask_sqlalchemy import SQLAlchemy

from app.models import Submission, Exam, Answer
from .base import BaseService


class SubmissionService(BaseService[Submission]):
    """考试提交服务类"""
    
    def __init__(self, db: SQLAlchemy):
        """初始化考试提交服务"""
        super().__init__(Submission, db)
    
    def get_by_exam_id(self, exam_id: int) -> List[Submission]:
        """根据考试ID获取提交记录
        
        Args:
            exam_id: 考试ID
            
        Returns:
            提交记录列表
        """
        return Submission.query.filter_by(exam_id=exam_id).order_by(Submission.submitted_at.desc()).all()
    
    def get_by_user_id(self, user_id: int) -> List[Submission]:
        """根据用户ID获取提交记录
        
        Args:
            user_id: 用户ID
            
        Returns:
            提交记录列表
        """
        return Submission.query.filter_by(user_id=user_id).order_by(Submission.submitted_at.desc()).all()
    
    def get_user_exam_submissions(self, user_id: int, exam_id: int) -> List[Submission]:
        """获取用户对特定考试的提交记录
        
        Args:
            user_id: 用户ID
            exam_id: 考试ID
            
        Returns:
            提交记录列表
        """
        return Submission.query.filter_by(
            user_id=user_id, 
            exam_id=exam_id
        ).order_by(Submission.submitted_at.desc()).all()
    
    def create_submission(self, exam_id: int, user_id: int,
                         started_at: Optional[datetime] = None,
                         submitted_at: Optional[datetime] = None) -> Submission:
        """创建新的考试提交记录
        
        Args:
            exam_id: 考试ID
            user_id: 用户ID
            started_at: 开始时间（None表示当前时间）
            submitted_at: 提交时间（None表示未提交）
            
        Returns:
            创建的提交记录
            
        Raises:
            ValueError: 考试不存在
        """
        # 验证考试存在
        exam = Exam.query.get(exam_id)
        if not exam:
            raise ValueError(f"考试ID {exam_id} 不存在")
        
        now = datetime.now(timezone.utc)
        if started_at is None:
            started_at = now
        
        # 计算状态
        status = 'in_progress'
        if submitted_at is not None:
            status = 'submitted'
        
        submission = self.create({
            'exam_id': exam_id,
            'user_id': user_id,
            'started_at': started_at,
            'submitted_at': submitted_at,
            'status': status,
            'total_score': 0.0,
            'obtained_score': 0.0
        })
        
        return submission
    
    def submit_exam(self, submission_id: int, answers: Dict[int, Any]) -> Dict[str, Any]:
        """提交考试答案并计算分数
        
        Args:
            submission_id: 提交记录ID
            answers: 答案字典 {question_id: answer}
            
        Returns:
            提交结果字典
        """
        submission = self.get_by_id(submission_id)
        if not submission:
            return {'success': False, 'error': '提交记录不存在'}
        
        if submission.status == 'submitted':
            return {'success': False, 'error': '考试已提交，不能重复提交'}
        
        # 验证提交时间
        exam = Exam.query.get(submission.exam_id)
        if not exam:
            return {'success': False, 'error': '考试不存在'}
        
        now = datetime.now(timezone.utc)
        if now > exam.end_time:
            return {'success': False, 'error': '考试已结束，不能提交'}
        
        # 更新提交时间
        submission.submitted_at = now
        submission.status = 'submitted'
        
        # 计算分数
        total_score = 0.0
        obtained_score = 0.0
        
        # 获取问题服务
        from .question_service import QuestionService
        question_service = QuestionService(self.db)
        
        # 处理每个答案
        for question_id, user_answer in answers.items():
            # 验证问题属于该考试
            question = question_service.get_by_id(question_id)
            if not question or question.exam_id != submission.exam_id:
                continue
            
            # 验证答案
            result = question_service.validate_answer(question_id, user_answer)
            
            # 记录答案
            answer = Answer(
                submission_id=submission_id,
                question_id=question_id,
                user_answer=str(user_answer) if not isinstance(user_answer, list) else ','.join(map(str, user_answer)),
                is_correct=result['is_correct'],
                score=result['score']
            )
            self.db.session.add(answer)
            
            total_score += result['question_score']
            obtained_score += result['score']
        
        # 更新分数
        submission.total_score = total_score
        submission.obtained_score = obtained_score
        
        # 计算百分比
        if total_score > 0:
            submission.score_percentage = (obtained_score / total_score) * 100
        else:
            submission.score_percentage = 0.0
        
        # 判断是否及格
        submission.is_passed = submission.score_percentage >= exam.pass_score
        
        self.db.session.commit()
        
        return {
            'success': True,
            'submission_id': submission_id,
            'total_score': total_score,
            'obtained_score': obtained_score,
            'score_percentage': submission.score_percentage,
            'is_passed': submission.is_passed,
            'exam_pass_score': exam.pass_score
        }
    
    def update_submission(self, id: int, **kwargs) -> Optional[Submission]:
        """更新提交记录
        
        Args:
            id: 提交记录ID
            **kwargs: 更新字段
            
        Returns:
            更新后的提交记录或None
        """
        instance = self.get_by_id(id)
        if not instance:
            return None
        
        # 验证考试存在
        if 'exam_id' in kwargs:
            exam = Exam.query.get(kwargs['exam_id'])
            if not exam:
                raise ValueError(f"考试ID {kwargs['exam_id']} 不存在")
        
        # 处理状态转换
        if 'status' in kwargs:
            new_status = kwargs['status']
            valid_statuses = ['in_progress', 'submitted', 'graded', 'archived']
            if new_status not in valid_statuses:
                raise ValueError(f"状态必须是: {', '.join(valid_statuses)}")
            
            # 如果状态改为submitted，设置提交时间
            if new_status == 'submitted' and instance.status != 'submitted':
                if 'submitted_at' not in kwargs:
                    kwargs['submitted_at'] = datetime.now(timezone.utc)
        
        return self.update(id, kwargs)
    
    def get_submission_details(self, submission_id: int) -> Dict[str, Any]:
        """获取提交详情
        
        Args:
            submission_id: 提交记录ID
            
        Returns:
            提交详情字典
        """
        submission = self.get_by_id(submission_id)
        if not submission:
            raise ValueError(f"提交记录ID {submission_id} 不存在")
        
        # 获取考试信息
        exam = Exam.query.get(submission.exam_id)
        
        # 获取答案列表
        answers = Answer.query.filter_by(submission_id=submission_id).all()
        
        # 获取问题详情
        answer_details = []
        for answer in answers:
            from .question_service import QuestionService
            question_service = QuestionService(self.db)
            question_detail = question_service.get_question_with_options(answer.question_id)
            
            answer_details.append({
                'answer': answer,
                'question': question_detail
            })
        
        return {
            'submission': submission,
            'exam': exam,
            'answers': answer_details,
            'answer_count': len(answers)
        }
    
    def calculate_statistics(self, exam_id: int) -> Dict[str, Any]:
        """计算考试统计信息
        
        Args:
            exam_id: 考试ID
            
        Returns:
            统计信息字典
        """
        # 获取所有提交记录
        submissions = self.get_by_exam_id(exam_id)
        
        if not submissions:
            return {
                'exam_id': exam_id,
                'total_submissions': 0,
                'average_score': 0,
                'pass_rate': 0,
                'score_distribution': {}
            }
        
        total_submissions = len(submissions)
        submitted_count = len([s for s in submissions if s.status == 'submitted'])
        
        if submitted_count == 0:
            return {
                'exam_id': exam_id,
                'total_submissions': total_submissions,
                'submitted_count': submitted_count,
                'average_score': 0,
                'pass_rate': 0,
                'score_distribution': {}
            }
        
        # 计算平均分
        total_score = sum(s.obtained_score for s in submissions if s.status == 'submitted')
        average_score = total_score / submitted_count
        
        # 计算及格率
        passed_count = len([s for s in submissions if s.status == 'submitted' and s.is_passed])
        pass_rate = (passed_count / submitted_count) * 100 if submitted_count > 0 else 0
        
        # 分数分布
        score_distribution = {}
        for s in submissions:
            if s.status == 'submitted':
                percentage = int(s.score_percentage // 10) * 10  # 按10分分段
                score_distribution[percentage] = score_distribution.get(percentage, 0) + 1
        
        return {
            'exam_id': exam_id,
            'total_submissions': total_submissions,
            'submitted_count': submitted_count,
            'average_score': round(average_score, 2),
            'pass_rate': round(pass_rate, 2),
            'passed_count': passed_count,
            'score_distribution': score_distribution
        }