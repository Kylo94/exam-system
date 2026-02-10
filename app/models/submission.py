"""答题提交模型"""

import json
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
from app.extensions import db
from .base import BaseModel


class Submission(BaseModel):
    """
    答题提交模型
    
    表示一次完整的答题提交记录
    """
    
    __tablename__ = 'submissions'
    
    # 字段定义
    exam_id = db.Column(
        db.Integer,
        db.ForeignKey('exams.id'),
        nullable=False,
        index=True,
        doc='试卷ID'
    )
    student_id = db.Column(
        db.String(50),
        nullable=True,
        index=True,
        doc='学生标识（扩展后可关联用户表）'
    )
    user_id = db.Column(
        db.Integer,
        db.ForeignKey('users.id'),
        nullable=True,
        index=True,
        doc='关联的用户ID'
    )
    student_name = db.Column(
        db.String(100),
        nullable=False,
        doc='学生姓名'
    )
    total_score = db.Column(
        db.Numeric(5, 2),
        default=0.0,
        nullable=False,
        doc='总分'
    )
    submit_time = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
        doc='提交时间'
    )
    duration_seconds = db.Column(
        db.Integer,
        default=0,
        nullable=False,
        doc='答题时长（秒）'
    )
    is_completed = db.Column(
        db.Boolean,
        default=True,
        nullable=False,
        doc='是否完成'
    )
    submission_metadata = db.Column(
        db.JSON,
        nullable=True,
        doc='提交元数据，如IP地址、浏览器信息等'
    )
    started_at = db.Column(
        db.DateTime,
        nullable=True,
        doc='开始时间'
    )
    submitted_at = db.Column(
        db.DateTime,
        nullable=True,
        doc='提交时间'
    )
    status = db.Column(
        db.String(20),
        default='in_progress',
        nullable=False,
        doc='状态（in_progress/submitted/graded/archived）'
    )
    obtained_score = db.Column(
        db.Float,
        nullable=True,
        doc='实际得分'
    )
    score_percentage = db.Column(
        db.Float,
        nullable=True,
        doc='得分百分比'
    )
    is_passed = db.Column(
        db.Boolean,
        nullable=True,
        doc='是否及格'
    )
    
    # 关系定义
    exam = db.relationship(
        'Exam',
        back_populates='submissions',
        lazy='joined',
        doc='关联的试卷'
    )
    answers = db.relationship(
        'Answer',
        back_populates='submission',
        lazy='dynamic',
        cascade='all, delete-orphan',
        doc='关联的答题记录'
    )
    
    def __init__(
        self,
        exam_id: int,
        student_name: str,
        student_id: Optional[str] = None,
        user_id: Optional[int] = None,
        total_score: float = 0.0,
        duration_seconds: int = 0,
        is_completed: bool = True,
        metadata: Optional[Dict[str, Any]] = None,
        started_at: Optional[datetime] = None,
        submitted_at: Optional[datetime] = None,
        status: str = 'in_progress',
        obtained_score: Optional[float] = None,
        score_percentage: Optional[float] = None,
        is_passed: Optional[bool] = None
    ):
        """
        初始化答题提交

        Args:
            exam_id: 试卷ID
            student_name: 学生姓名
            student_id: 学生标识（可选）
            user_id: 关联的用户ID（可选）
            total_score: 总分，默认0.0
            duration_seconds: 答题时长（秒），默认0
            is_completed: 是否完成，默认True
            metadata: 提交元数据（可选）
            started_at: 开始时间（可选）
            submitted_at: 提交时间（可选）
            status: 状态，默认'in_progress'
            obtained_score: 实际得分（可选）
            score_percentage: 得分百分比（可选）
            is_passed: 是否及格（可选）
        """
        self.exam_id = exam_id
        self.student_name = student_name
        self.student_id = student_id
        self.user_id = user_id
        self.total_score = total_score
        self.duration_seconds = duration_seconds
        self.is_completed = is_completed
        self.submission_metadata = metadata or {}
        self.submit_time = datetime.now(timezone.utc)
        self.started_at = started_at
        self.submitted_at = submitted_at
        self.status = status
        self.obtained_score = obtained_score
        self.score_percentage = score_percentage
        self.is_passed = is_passed
    
    @classmethod
    def get_by_student(cls, student_id: str) -> List['Submission']:
        """
        根据学生ID获取所有提交记录
        
        Args:
            student_id: 学生ID
            
        Returns:
            提交记录列表，按提交时间倒序排列
        """
        return (
            cls.query
            .filter_by(student_id=student_id)
            .order_by(cls.submit_time.desc())
            .all()
        )
    
    @classmethod
    def get_by_exam(cls, exam_id: int, limit: int = 50) -> List['Submission']:
        """
        根据试卷ID获取提交记录
        
        Args:
            exam_id: 试卷ID
            limit: 返回数量限制
            
        Returns:
            提交记录列表，按提交时间倒序排列
        """
        return (
            cls.query
            .filter_by(exam_id=exam_id)
            .order_by(cls.submit_time.desc())
            .limit(limit)
            .all()
        )
    
    def calculate_score(self) -> float:
        """
        计算总分（基于所有答题记录）
        
        Returns:
            总分
        """
        answers = self.answers.all()
        if not answers:
            return 0.0
        
        total = sum(float(answer.score) for answer in answers)
        self.total_score = total
        db.session.commit()
        return total
    
    def get_correct_count(self) -> int:
        """
        获取答对题目数量
        
        Returns:
            答对题目数量
        """
        return self.answers.filter_by(is_correct=True).count()
    
    def get_total_questions(self) -> int:
        """
        获取总题目数量
        
        Returns:
            总题目数量
        """
        return self.answers.count()
    
    def get_correct_rate(self) -> float:
        """
        获取正确率
        
        Returns:
            正确率（0-1）
        """
        total = self.get_total_questions()
        if total == 0:
            return 0.0
        return self.get_correct_count() / total
    
    def get_duration_formatted(self) -> str:
        """
        获取格式化的答题时长
        
        Returns:
            格式化的时长字符串，如"1小时30分15秒"
        """
        seconds = self.duration_seconds
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        
        parts = []
        if hours > 0:
            parts.append(f"{hours}小时")
        if minutes > 0:
            parts.append(f"{minutes}分")
        parts.append(f"{secs}秒")
        
        return "".join(parts) if parts else "0秒"
    
    def to_dict(self, include_answers: bool = False) -> dict:
        """
        转换为字典，可包含关联的答题记录
        
        Args:
            include_answers: 是否包含答题记录
            
        Returns:
            包含提交信息的字典
        """
        data = super().to_dict()
        
        # 处理JSON字段
        if 'metadata' in data and data['metadata']:
            if isinstance(data['metadata'], str):
                try:
                    data['metadata'] = json.loads(data['metadata'])
                except json.JSONDecodeError:
                    data['metadata'] = {}
        
        # 添加统计信息
        data['correct_count'] = self.get_correct_count()
        data['total_questions'] = self.get_total_questions()
        data['correct_rate'] = self.get_correct_rate()
        data['duration_formatted'] = self.get_duration_formatted()
        
        # 添加关联信息
        if self.exam:
            data['exam_title'] = self.exam.title
        
        if include_answers:
            data['answers'] = [answer.to_dict() for answer in self.answers.all()]
        
        return data
    
    def __repr__(self) -> str:
        """友好的字符串表示"""
        return f'<Submission id={self.id} exam_id={self.exam_id} student="{self.student_name}">'