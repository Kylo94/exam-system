"""考试服务模块"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from flask_sqlalchemy import SQLAlchemy

from app.models import Exam, Subject, Level
from .base import BaseService


class ExamService(BaseService[Exam]):
    """考试服务类"""
    
    def __init__(self, db: SQLAlchemy):
        """初始化考试服务"""
        super().__init__(Exam, db)
    
    def get_by_subject_id(self, subject_id: int) -> List[Exam]:
        """根据科目ID获取考试
        
        Args:
            subject_id: 科目ID
            
        Returns:
            考试列表
        """
        return Exam.query.filter_by(subject_id=subject_id).order_by(Exam.created_at.desc()).all()
    
    def get_by_level_id(self, level_id: int) -> List[Exam]:
        """根据难度级别ID获取考试
        
        Args:
            level_id: 难度级别ID
            
        Returns:
            考试列表
        """
        return Exam.query.filter_by(level_id=level_id).order_by(Exam.created_at.desc()).all()
    
    def get_active_exams(self) -> List[Exam]:
        """获取所有活跃考试
        
        Returns:
            活跃考试列表
        """
        return Exam.query.filter_by(is_active=True).order_by(Exam.created_at.desc()).all()
    
    def get_upcoming_exams(self) -> List[Exam]:
        """获取即将开始的考试（未开始且未过期）
        
        Returns:
            即将开始的考试列表
        """
        now = datetime.utcnow()
        return Exam.query.filter(
            Exam.start_time > now,
            Exam.is_active == True
        ).order_by(Exam.start_time).all()
    
    def get_ongoing_exams(self) -> List[Exam]:
        """获取进行中的考试
        
        Returns:
            进行中的考试列表
        """
        now = datetime.utcnow()
        return Exam.query.filter(
            Exam.start_time <= now,
            Exam.end_time >= now,
            Exam.is_active == True
        ).order_by(Exam.end_time).all()
    
    def get_completed_exams(self) -> List[Exam]:
        """获取已结束的考试
        
        Returns:
            已结束的考试列表
        """
        now = datetime.utcnow()
        return Exam.query.filter(
            Exam.end_time < now,
            Exam.is_active == True
        ).order_by(Exam.end_time.desc()).all()
    
    def create_exam(self, title: str, subject_id: int, level_id: int,
                    description: str = "", duration_minutes: int = 60,
                    start_time: Optional[datetime] = None,
                    end_time: Optional[datetime] = None,
                    is_active: bool = True, max_attempts: int = 1,
                    pass_score: float = 60.0, total_points: int = 100) -> Exam:
        """创建新考试

        Args:
            title: 考试标题
            subject_id: 科目ID
            level_id: 难度级别ID
            description: 考试描述
            duration_minutes: 考试时长（分钟）
            start_time: 开始时间（None表示立即开始）
            end_time: 结束时间（None表示无结束时间限制）
            is_active: 是否活跃
            max_attempts: 最大尝试次数
            pass_score: 及格分数
            total_points: 总分

        Returns:
            创建的考试

        Raises:
            ValueError: 科目或难度级别不存在，或数据验证失败
        """
        # 验证科目存在
        subject = Subject.query.get(subject_id)
        if not subject:
            raise ValueError(f"科目ID {subject_id} 不存在")
        
        # 验证难度级别存在
        level = Level.query.get(level_id)
        if not level:
            raise ValueError(f"难度级别ID {level_id} 不存在")
        
        # 设置默认时间
        now = datetime.utcnow()
        if start_time is None:
            start_time = now
        
        if end_time is None:
            # 默认结束时间为开始时间后30天
            end_time = start_time + timedelta(days=30)
        
        # 验证时间逻辑
        if end_time <= start_time:
            raise ValueError("结束时间必须晚于开始时间")

        if duration_minutes is not None and duration_minutes <= 0:
            raise ValueError("考试时长必须大于0")
        
        if max_attempts < 1:
            raise ValueError("最大尝试次数必须大于0")

        if pass_score < 0 or pass_score > 100:
            raise ValueError("及格分数必须在0-100之间")

        if total_points < 1:
            raise ValueError("总分必须大于0")

        return self.create({
            'title': title,
            'description': description,
            'subject_id': subject_id,
            'level_id': level_id,
            'total_points': total_points,
            'duration_minutes': duration_minutes,
            'start_time': start_time,
            'end_time': end_time,
            'is_active': is_active,
            'max_attempts': max_attempts,
            'pass_score': pass_score
        })
    
    def update_exam(self, id: int, **kwargs) -> Optional[Exam]:
        """更新考试信息
        
        Args:
            id: 考试ID
            **kwargs: 更新字段
            
        Returns:
            更新后的考试或None
            
        Raises:
            ValueError: 数据验证失败
        """
        instance = self.get_by_id(id)
        if not instance:
            return None
        
        # 验证科目存在
        if 'subject_id' in kwargs:
            subject = Subject.query.get(kwargs['subject_id'])
            if not subject:
                raise ValueError(f"科目ID {kwargs['subject_id']} 不存在")
        
        # 验证难度级别存在
        if 'level_id' in kwargs:
            level = Level.query.get(kwargs['level_id'])
            if not level:
                raise ValueError(f"难度级别ID {kwargs['level_id']} 不存在")
        
        # 验证时间逻辑
        start_time = kwargs.get('start_time', instance.start_time)
        end_time = kwargs.get('end_time', instance.end_time)

        # 只有两个时间都有值时才进行比较
        if start_time is not None and end_time is not None:
            if end_time <= start_time:
                raise ValueError("结束时间必须晚于开始时间")

        # 验证数值范围
        if 'duration_minutes' in kwargs and kwargs['duration_minutes'] is not None and kwargs['duration_minutes'] <= 0:
            raise ValueError("考试时长必须大于0")

        if 'max_attempts' in kwargs and kwargs['max_attempts'] is not None and kwargs['max_attempts'] < 1:
            raise ValueError("最大尝试次数必须大于0")
        
        if 'pass_score' in kwargs:
            pass_score = kwargs['pass_score']
            if pass_score < 0 or pass_score > 100:
                raise ValueError("及格分数必须在0-100之间")
        
        return self.update(id, kwargs)
    
    def search_exams(self, title: Optional[str] = None,
                    subject_id: Optional[int] = None,
                    level_id: Optional[int] = None,
                    is_active: Optional[bool] = None,
                    skip: int = 0, limit: int = 100) -> List[Exam]:
        """搜索考试
        
        Args:
            title: 考试标题（模糊搜索）
            subject_id: 科目ID
            level_id: 难度级别ID
            is_active: 是否活跃
            skip: 跳过的记录数
            limit: 返回的最大记录数
            
        Returns:
            考试列表
        """
        query = Exam.query
        
        if title:
            query = query.filter(Exam.title.ilike(f"%{title}%"))
        
        if subject_id is not None:
            query = query.filter_by(subject_id=subject_id)
        
        if level_id is not None:
            query = query.filter_by(level_id=level_id)
        
        if is_active is not None:
            query = query.filter_by(is_active=is_active)
        
        query = query.order_by(Exam.created_at.desc())
        
        return query.offset(skip).limit(limit).all()
    
    def get_exam_status(self, exam_id: int) -> Dict[str, Any]:
        """获取考试状态信息
        
        Args:
            exam_id: 考试ID
            
        Returns:
            状态信息字典
        """
        exam = self.get_by_id(exam_id)
        if not exam:
            raise ValueError(f"考试ID {exam_id} 不存在")
        
        now = datetime.utcnow()

        # 处理 None 的时间值
        start_time = exam.start_time if exam.start_time else datetime.min
        end_time = exam.end_time if exam.end_time else datetime.max

        status = {
            'exam': exam,
            'current_time': now,
            'is_upcoming': start_time > now,
            'is_ongoing': start_time <= now <= end_time,
            'is_completed': end_time < now,
            'is_expired': end_time < now,
            'time_remaining': None,
            'has_started': start_time <= now,
            'has_ended': end_time < now
        }
        
        if status['is_ongoing']:
            status['time_remaining'] = exam.end_time - now
        elif status['is_upcoming']:
            status['time_remaining'] = exam.start_time - now
        
        return status
    
    def can_start_exam(self, exam_id: int, user_id: Optional[int] = None) -> Dict[str, Any]:
        """检查是否可以开始考试
        
        Args:
            exam_id: 考试ID
            user_id: 用户ID（可选，用于检查尝试次数）
            
        Returns:
            检查结果字典
        """
        exam = self.get_by_id(exam_id)
        if not exam:
            return {'can_start': False, 'reason': '考试不存在'}
        
        if not exam.is_active:
            return {'can_start': False, 'reason': '考试未启用'}
        
        now = datetime.utcnow()
        if now < exam.start_time:
            return {'can_start': False, 'reason': '考试尚未开始'}
        
        if now > exam.end_time:
            return {'can_start': False, 'reason': '考试已结束'}
        
        # 检查用户尝试次数（只有在max_attempts大于0时才检查）
        if user_id and exam.max_attempts and exam.max_attempts > 0:
            from app.models import Submission
            attempt_count = Submission.query.filter_by(
                exam_id=exam_id,
                user_id=user_id
            ).filter(Submission.status.in_(['submitted', 'graded'])).count()

            if attempt_count >= exam.max_attempts:
                return {
                    'can_start': False,
                    'reason': f'已达到最大尝试次数（{exam.max_attempts}次）'
                }
        
        return {'can_start': True, 'reason': ''}
    
    def get_exam_statistics(self, exam_id: int) -> Dict[str, Any]:
        """获取考试统计数据
        
        Args:
            exam_id: 考试ID
            
        Returns:
            统计数据字典
        """
        exam = self.get_by_id(exam_id)
        if not exam:
            raise ValueError(f"考试ID {exam_id} 不存在")
        
        # 获取提交记录统计
        from app.models import Submission
        submissions = Submission.query.filter_by(exam_id=exam_id).all()

        total_submissions = len(submissions)
        completed_submissions = [s for s in submissions if s.status in ['submitted', 'graded', 'archived']]
        passed_submissions = [s for s in completed_submissions if s.is_passed]

        # 计算平均分 - 包含所有有分数的已完成提交
        scored_submissions = [s for s in completed_submissions
                             if s.obtained_score is not None]
        
        if scored_submissions:
            average_score = sum(s.obtained_score for s in scored_submissions) / len(scored_submissions)
            average_percentage = sum(s.obtained_score / s.total_score * 100 
                                   for s in scored_submissions) / len(scored_submissions)
        else:
            average_score = 0
            average_percentage = 0
        
        # 计算及格率
        if completed_submissions:
            pass_rate = len(passed_submissions) / len(completed_submissions) * 100
        else:
            pass_rate = 0
        
        # 获取题目统计
        from app.models import Question
        questions = Question.query.filter_by(exam_id=exam_id).all()
        question_count = len(questions)
        # 安全计算总分，跳过非数值类型的points
        total_score = sum(q.points if isinstance(q.points, (int, float)) else 0 for q in questions)

        return {
            'exam_id': exam.id,
            'exam_title': exam.title,
            'question_count': question_count,
            'total_score': total_score,
            'total_submissions': total_submissions,
            'completed_submissions': len(completed_submissions),
            'passed_count': len(passed_submissions),
            'passed_submissions': len(passed_submissions),
            'average_score': round(average_score, 2),
            'average_percentage': round(average_percentage, 2),
            'pass_rate': round(pass_rate, 2),
            'max_attempts': exam.max_attempts,
            'pass_score': exam.pass_score,
        }