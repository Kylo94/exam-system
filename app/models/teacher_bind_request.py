"""绑定申请模型"""

from datetime import datetime, timezone
from typing import Optional, Dict, Any
from app.extensions import db
from .base import BaseModel


class TeacherBindRequest(BaseModel):
    """
    教师-学生绑定申请模型

    属性:
        student_id: 学生ID
        teacher_id: 教师ID
        status: 申请状态（pending/approved/rejected）
        message: 申请消息
        reviewed_at: 审核时间
        reviewed_by: 审核人ID（管理员）
    """

    __tablename__ = 'teacher_bind_requests'

    student_id = db.Column(
        db.Integer,
        db.ForeignKey('users.id'),
        nullable=False,
        index=True,
        doc='学生ID'
    )

    teacher_id = db.Column(
        db.Integer,
        db.ForeignKey('users.id'),
        nullable=False,
        index=True,
        doc='教师ID'
    )

    status = db.Column(
        db.String(20),
        nullable=False,
        default='pending',
        doc='申请状态（pending/approved/rejected）'
    )

    message = db.Column(
        db.Text,
        nullable=True,
        doc='申请消息'
    )

    reviewed_at = db.Column(
        db.DateTime,
        nullable=True,
        doc='审核时间'
    )

    reviewed_by = db.Column(
        db.Integer,
        db.ForeignKey('users.id'),
        nullable=True,
        doc='审核人ID（教师本人）'
    )

    # 关系
    student = db.relationship(
        'User',
        foreign_keys=[student_id],
        backref='bind_requests',
        doc='申请的学生'
    )

    teacher = db.relationship(
        'User',
        foreign_keys=[teacher_id],
        backref='pending_bind_requests',
        doc='申请的教师'
    )

    reviewer = db.relationship(
        'User',
        foreign_keys=[reviewed_by],
        backref='reviewed_bind_requests',
        doc='审核人'
    )

    def __init__(
        self,
        student_id: int,
        teacher_id: int,
        message: Optional[str] = None,
        status: str = 'pending'
    ):
        """
        初始化绑定申请

        Args:
            student_id: 学生ID
            teacher_id: 教师ID
            message: 申请消息
            status: 申请状态
        """
        super().__init__()
        self.student_id = student_id
        self.teacher_id = teacher_id
        self.message = message
        self.status = status

    def approve(self, reviewer_id: int) -> bool:
        """
        批准申请

        Args:
            reviewer_id: 审核人ID（教师ID）

        Returns:
            是否批准成功
        """
        if self.status != 'pending':
            return False

        self.status = 'approved'
        self.reviewed_at = datetime.now(timezone.utc)
        self.reviewed_by = reviewer_id

        # 绑定学生和教师
        from app.models.user import User
        student = User.get_by_id(self.student_id)
        if student:
            student.bind_teacher(self.teacher_id)

        db.session.commit()
        return True

    def reject(self, reviewer_id: int, reason: Optional[str] = None) -> bool:
        """
        拒绝申请

        Args:
            reviewer_id: 审核人ID（教师ID）
            reason: 拒绝原因

        Returns:
            是否拒绝成功
        """
        if self.status != 'pending':
            return False

        self.status = 'rejected'
        self.reviewed_at = datetime.now(timezone.utc)
        self.reviewed_by = reviewer_id

        if reason:
            self.message = f"{self.message or ''}\n拒绝原因: {reason}" if self.message else reason

        db.session.commit()
        return True

    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典

        Returns:
            申请信息字典
        """
        data = super().to_dict()

        # 添加学生信息
        if self.student:
            data['student'] = {
                'id': self.student.id,
                'username': self.student.username,
                'email': self.student.email
            }

        # 添加教师信息
        if self.teacher:
            data['teacher'] = {
                'id': self.teacher.id,
                'username': self.teacher.username
            }

        return data

    @classmethod
    def get_pending_requests(cls, teacher_id: Optional[int] = None):
        """
        获取待处理的申请

        Args:
            teacher_id: 教师ID（可选，如果提供则只返回该教师的申请）

        Returns:
            待处理申请列表
        """
        query = cls.query.filter_by(status='pending')

        if teacher_id:
            query = query.filter_by(teacher_id=teacher_id)

        return query.order_by(cls.created_at.desc()).all()

    @classmethod
    def get_student_pending_request(cls, student_id: int):
        """
        获取学生的待处理申请

        Args:
            student_id: 学生ID

        Returns:
            待处理申请或None
        """
        return cls.query.filter_by(
            student_id=student_id,
            status='pending'
        ).first()

    @classmethod
    def check_existing_request(cls, student_id: int, teacher_id: int, status: Optional[str] = None) -> Optional['TeacherBindRequest']:
        """
        检查是否已存在申请

        Args:
            student_id: 学生ID
            teacher_id: 教师ID
            status: 状态筛选（可选）

        Returns:
            申请记录或None
        """
        query = cls.query.filter_by(
            student_id=student_id,
            teacher_id=teacher_id
        )

        if status:
            query = query.filter_by(status=status)

        return query.first()

    def __repr__(self) -> str:
        return f'<TeacherBindRequest {self.student_id}->{self.teacher_id} ({self.status})>'
