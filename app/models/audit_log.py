"""
审计日志模型
"""
from tortoise import fields
from tortoise.models import Model


class AuditLog(Model):
    """审计日志模型"""

    id = fields.IntField(pk=True)
    user_id = fields.IntField(null=True, description="操作用户ID")
    username = fields.CharField(max_length=100, null=True, description="操作用户名")
    action = fields.CharField(max_length=50, description="操作类型")
    resource = fields.CharField(max_length=50, description="资源类型")
    resource_id = fields.IntField(null=True, description="资源ID")
    description = fields.TextField(null=True, description="操作描述")
    ip_address = fields.CharField(max_length=50, null=True, description="IP地址")
    user_agent = fields.TextField(null=True, description="User Agent")
    status = fields.CharField(max_length=20, default="success", description="操作状态: success, failed")
    details = fields.JSONField(default={}, description="额外详情")
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "audit_logs"
        ordering = ["-created_at"]

    def __str__(self):
        return f"<AuditLog {self.id}: {self.action} {self.resource}>"

    @classmethod
    async def log(
        cls,
        action: str,
        resource: str,
        user=None,
        resource_id: int = None,
        description: str = None,
        ip_address: str = None,
        user_agent: str = None,
        status: str = "success",
        details: dict = None
    ):
        """记录日志"""
        return await cls.create(
            user_id=user.id if user else None,
            username=user.username if user else "系统",
            action=action,
            resource=resource,
            resource_id=resource_id,
            description=description,
            ip_address=ip_address,
            user_agent=user_agent,
            status=status,
            details=details or {}
        )

    @classmethod
    async def log_create(cls, user, resource_type: str, resource_id: int, description: str = None, **kwargs):
        """记录创建操作"""
        await cls.log(
            action="create",
            resource=resource_type,
            user=user,
            resource_id=resource_id,
            description=description or f"创建{resource_type}",
            **kwargs
        )

    @classmethod
    async def log_update(cls, user, resource_type: str, resource_id: int, description: str = None, **kwargs):
        """记录更新操作"""
        await cls.log(
            action="update",
            resource=resource_type,
            user=user,
            resource_id=resource_id,
            description=description or f"更新{resource_type}",
            **kwargs
        )

    @classmethod
    async def log_delete(cls, user, resource_type: str, resource_id: int, description: str = None, **kwargs):
        """记录删除操作"""
        await cls.log(
            action="delete",
            resource=resource_type,
            user=user,
            resource_id=resource_id,
            description=description or f"删除{resource_type}",
            **kwargs
        )

    @classmethod
    async def log_login(cls, user, ip_address: str = None, user_agent: str = None, status: str = "success"):
        """记录登录"""
        await cls.log(
            action="login",
            resource="auth",
            user=user,
            description=f"用户登录" if status == "success" else "登录失败",
            ip_address=ip_address,
            user_agent=user_agent,
            status=status
        )

    @classmethod
    async def log_logout(cls, user, ip_address: str = None, user_agent: str = None):
        """记录登出"""
        await cls.log(
            action="logout",
            resource="auth",
            user=user,
            description="用户登出",
            ip_address=ip_address,
            user_agent=user_agent
        )
