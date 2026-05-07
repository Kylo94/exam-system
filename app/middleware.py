"""
全局异常处理中间件
"""
import logging

from fastapi import Request, status
from fastapi.exceptions import HTTPException
from fastapi.responses import JSONResponse
from tortoise.exceptions import DoesNotExist, FieldError, IntegrityError

from app.services.exceptions import (
    AppException,
)
from app.templating import templates

logger = logging.getLogger(__name__)


async def http_exception_handler(request: Request, exc: HTTPException):
    """HTTPException处理"""
    if request.url.path.startswith("/api/"):
        return JSONResponse(
            status_code=exc.status_code,
            content={"success": False, "message": exc.detail, "code": "HTTP_ERROR"}
        )
    # HTML页面请求返回错误页
    return templates.TemplateResponse(
        f"errors/{exc.status_code}.html",
        {"request": request, "error": exc.detail},
        status_code=exc.status_code
    )


async def app_exception_handler(request: Request, exc: AppException):
    """应用自定义异常处理"""
    status_code = status.HTTP_400_BAD_REQUEST
    if exc.code == "NOT_FOUND":
        status_code = status.HTTP_404_NOT_FOUND
    elif exc.code == "PERMISSION_DENIED":
        status_code = status.HTTP_403_FORBIDDEN
    elif exc.code == "VALIDATION_ERROR":
        status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    elif exc.code == "DUPLICATE":
        status_code = status.HTTP_409_CONFLICT

    if request.url.path.startswith("/api/"):
        return JSONResponse(
            status_code=status_code,
            content={"success": False, "message": exc.message, "code": exc.code}
        )
    return templates.TemplateResponse(
        "errors/400.html",
        {"request": request, "error": exc.message},
        status_code=status_code
    )


async def integrity_error_handler(request: Request, exc: IntegrityError):
    """数据库完整性错误"""
    logger.warning(f"数据库完整性错误: {exc}")
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={"success": False, "message": "数据冲突，请检查是否已存在重复记录", "code": "DUPLICATE"}
    )


async def field_error_handler(request: Request, exc: FieldError):
    """字段验证错误"""
    logger.warning(f"字段错误: {exc}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"success": False, "message": f"字段验证失败: {str(exc)}", "code": "VALIDATION_ERROR"}
    )


async def does_not_exist_handler(request: Request, exc: DoesNotExist):
    """资源不存在错误"""
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={"success": False, "message": "请求的资源不存在", "code": "NOT_FOUND"}
    )


async def general_exception_handler(request: Request, exc: Exception):
    """通用异常处理"""
    error_logger = logging.getLogger("error")
    error_logger.exception(f"未处理的异常 | 请求: {request.url.path} | 错误: {str(exc)}")

    if request.url.path.startswith("/api/"):
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"success": False, "message": "服务器内部错误", "code": "INTERNAL_ERROR"}
        )
    return templates.TemplateResponse(
        "errors/500.html",
        {"request": request, "error": str(exc)},
        status_code=500
    )


def register_exception_handlers(app):
    """注册所有异常处理器"""
    from fastapi.exceptions import HTTPException

    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(AppException, app_exception_handler)
    app.add_exception_handler(IntegrityError, integrity_error_handler)
    app.add_exception_handler(FieldError, field_error_handler)
    app.add_exception_handler(DoesNotExist, does_not_exist_handler)
    app.add_exception_handler(Exception, general_exception_handler)
