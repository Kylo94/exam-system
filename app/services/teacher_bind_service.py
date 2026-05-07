"""
师生绑定服务
"""
from typing import List, Optional, Tuple
from app.models.user import User
from app.models.teacher_bind_request import TeacherBindRequest


class TeacherBindService:
    """师生绑定服务"""

    @staticmethod
    async def create_bind_request(student_id: int, teacher_id: int, message: str = "") -> TeacherBindRequest:
        """创建绑定申请"""
        # 检查是否已有待处理或已通过的申请
        existing = await TeacherBindRequest.filter(
            student_id=student_id,
            status__in=["pending", "approved"]
        ).first()
        if existing:
            if existing.status == "approved":
                raise ValueError("该学生已经绑定了一位教师，无法再次申请")
            raise ValueError("该学生有待处理的绑定申请")

        # 检查教师是否存在
        teacher = await User.get_or_none(id=teacher_id, role="teacher")
        if not teacher:
            raise ValueError("教师不存在")

        return await TeacherBindRequest.create(
            student_id=student_id,
            teacher_id=teacher_id,
            message=message
        )

    @staticmethod
    async def approve_bind_request(request_id: int, teacher_id: int = None) -> TeacherBindRequest:
        """批准绑定申请"""
        bind_request = await TeacherBindRequest.get_or_none(id=request_id)
        if not bind_request:
            raise ValueError("申请不存在")

        # 如果提供了teacher_id，验证是否为该教师的申请
        if teacher_id and bind_request.teacher_id != teacher_id:
            raise ValueError("无权批准此申请")

        if bind_request.status != "pending":
            raise ValueError("只能批准待处理的申请")

        # 更新学生绑定教师
        student = await User.get_or_none(id=bind_request.student_id)
        if student:
            student.teacher_id = bind_request.teacher_id
            await student.save()

        bind_request.status = "approved"
        await bind_request.save()
        return bind_request

    @staticmethod
    async def reject_bind_request(request_id: int, teacher_id: int = None) -> TeacherBindRequest:
        """拒绝绑定申请"""
        bind_request = await TeacherBindRequest.get_or_none(id=request_id)
        if not bind_request:
            raise ValueError("申请不存在")

        # 如果提供了teacher_id，验证是否为该教师的申请
        if teacher_id and bind_request.teacher_id != teacher_id:
            raise ValueError("无权拒绝此申请")

        if bind_request.status != "pending":
            raise ValueError("只能拒绝待处理的申请")

        bind_request.status = "rejected"
        await bind_request.save()
        return bind_request

    @staticmethod
    async def cancel_bind_request(student_id: int) -> bool:
        """取消绑定申请（学生主动取消）"""
        pending = await TeacherBindRequest.filter(
            student_id=student_id,
            status="pending"
        ).first()
        if pending:
            await pending.delete()
            return True
        return False

    @staticmethod
    async def get_pending_requests_for_teacher(teacher_id: int) -> List[TeacherBindRequest]:
        """获取教师待处理的绑定申请"""
        return await TeacherBindRequest.filter(
            teacher_id=teacher_id,
            status="pending"
        ).prefetch_related("student").order_by("-created_at")

    @staticmethod
    async def get_all_pending_requests() -> List[TeacherBindRequest]:
        """获取所有待处理的绑定申请（管理员）"""
        return await TeacherBindRequest.filter(
            status="pending"
        ).prefetch_related("student", "teacher").order_by("-created_at")
