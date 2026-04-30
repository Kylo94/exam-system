"""服务层异常定义"""
from typing import Optional


class AppException(Exception):
    """应用基础异常"""

    def __init__(self, message: str, code: str = "APP_ERROR"):
        self.message = message
        self.code = code
        super().__init__(self.message)


class NotFoundException(AppException):
    """资源不存在"""

    def __init__(self, resource: str, resource_id: Optional[int] = None):
        msg = f"{resource}不存在"
        if resource_id:
            msg += f" (ID: {resource_id})"
        super().__init__(msg, code="NOT_FOUND")


class PermissionDeniedException(AppException):
    """权限不足"""

    def __init__(self, message: str = "权限不足"):
        super().__init__(message, code="PERMISSION_DENIED")


class ValidationException(AppException):
    """验证失败"""

    def __init__(self, message: str):
        super().__init__(message, code="VALIDATION_ERROR")


class DuplicateException(AppException):
    """重复资源"""

    def __init__(self, resource: str, field: str):
        super().__init__(f"{resource}已存在 ({field})", code="DUPLICATE")
