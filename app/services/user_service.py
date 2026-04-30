"""用户服务"""
from typing import Optional, List
from app.models.user import User
from app.auth import get_password_hash
from app.services.exceptions import NotFoundException, ValidationException, DuplicateException


class UserService:
    """用户业务逻辑"""

    @staticmethod
    async def get_user_or_404(user_id: int) -> User:
        """获取用户，不存在则抛异常"""
        user = await User.get_or_none(id=user_id)
        if not user:
            raise NotFoundException("用户", user_id)
        return user

    @staticmethod
    async def get_by_username(username: str) -> Optional[User]:
        """根据用户名获取用户"""
        return await User.get_or_none(username=username)

    @staticmethod
    async def get_by_email(email: str) -> Optional[User]:
        """根据邮箱获取用户"""
        return await User.get_or_none(email=email)

    @staticmethod
    async def create_user(
        username: str,
        email: str,
        password: str,
        role: str = "student",
    ) -> User:
        """创建用户"""
        if await UserService.get_by_username(username):
            raise DuplicateException("用户名", username)

        if await UserService.get_by_email(email):
            raise DuplicateException("邮箱", email)

        if role not in ["admin", "teacher", "student"]:
            raise ValidationException("无效的角色")

        return await User.create(
            username=username,
            email=email,
            password_hash=get_password_hash(password),
            role=role,
        )

    @staticmethod
    async def toggle_active(user_id: int, current_user_id: int) -> User:
        """切换用户激活状态"""
        if user_id == current_user_id:
            raise ValidationException("不能禁用自己")

        user = await UserService.get_user_or_404(user_id)
        user.is_active = not user.is_active
        await user.save()
        return user

    @staticmethod
    async def change_role(user_id: int, role: str) -> User:
        """修改用户角色"""
        if role not in ["admin", "teacher", "student"]:
            raise ValidationException("无效的角色")

        user = await UserService.get_user_or_404(user_id)
        user.role = role
        await user.save()
        return user

    @staticmethod
    async def list_users(
        role: str = None,
        search: str = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[List[User], int]:
        """分页查询用户

        Returns:
            (用户列表, 总数)
        """
        query = User.all()

        if role:
            query = query.filter(role=role)
        if search:
            from tortoise.queryset import Q
            query = query.filter(Q(username__contains=search) | Q(email__contains=search))

        total = await query.count()
        offset = (page - 1) * page_size
        users = await query.order_by("-created_at").offset(offset).limit(page_size)

        return users, total