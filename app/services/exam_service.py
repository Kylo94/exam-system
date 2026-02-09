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
                    pass_score: float = 60.0) -> Exam:
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
        
        if duration_minutes <= 0:
            raise ValueError("考试时长必须大于0")
        
        if max_attempts < 1:
            raise ValueError("最大尝试次数必须大于0")
        
        if pass_score < 0 or pass_score > 100:
            raise ValueError("及格分数必须在0-100之间")
        
        return self.create({
            'title': title,
            'description': description,
            'subject_id': subject_id,
            'level_id': level_id,
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
        
        if end_time <= start_time:
            raise ValueError("结束时间必须晚于开始时间")
        
        # 验证数值范围
        if 'duration_minutes' in kwargs and kwargs['duration_minutes'] <= 0:
            raise ValueError("考试时长必须大于0")
        
        if 'max_attempts' in kwargs and kwargs['max_attempts'] < 1:
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
        status = {
            'exam': exam,
            'current_time': now,
            'is_upcoming': exam.start_time > now,
            'is_ongoing': exam.start_time <= now <= exam.end_time,
            'is_completed': exam.end_time < now,
            'is_expired': exam.end_time < now,
            'time_remaining': None,
            'has_started': exam.start_time <= now,
            'has_ended': exam.end_time < now
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
        
        # TODO: 检查用户尝试次数（需要用户认证系统）
        # if user_id:
        #     attempt_count = Submission.query.filter_by(
        #         exam_id=exam_id, user_id=user_id
        #     ).count()
        #     if attempt_count >= exam.max_attempts:
        #         return {'can_start': False, 'reason': '已达到最大尝试次数'}
        
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
        
        # TODO: 实现统计数据（需要提交记录）
        # 目前返回基本数据，后续可以添加提交数量、平均分等
        
        return {
            'exam': exam,
            'question_count': exam.questions.count() if hasattr(exam, 'questions') else 0,
            'total_score': sum(q.score for q in exam.questions) if hasattr(exam, 'questions') else 0,
            # 'submission_count': 0,
            # 'average_score': 0,
            # 'pass_rate': 0,
        }