"""标准化API响应工具模块

提供统一的API响应格式，确保前后端数据交互的一致性。
"""

from typing import Any, Dict, List, Optional
from flask import jsonify


def success_response(
    data: Optional[Any] = None,
    message: str = "操作成功",
    status_code: int = 200
) -> tuple:
    """成功响应
    
    Args:
        data: 响应数据，可以是任意类型
        message: 成功消息
        status_code: HTTP状态码，默认200
        
    Returns:
        (response, status_code) 元组
    """
    response_data: Dict[str, Any] = {
        "success": True,
        "message": message,
        "data": data
    }
    
    # 移除可能为None的字段
    if data is None:
        response_data.pop("data")
    
    return jsonify(response_data), status_code


def error_response(
    message: str = "操作失败",
    status_code: int = 400,
    code: Optional[int] = None,
    details: Optional[Dict[str, Any]] = None
) -> tuple:
    """错误响应
    
    Args:
        message: 错误消息
        status_code: HTTP状态码，默认400
        code: 业务错误码，默认与status_code相同
        details: 错误详情
        
    Returns:
        (response, status_code) 元组
    """
    response_data = {
        "success": False,
        "message": message,
        "code": code or status_code
    }
    
    if details:
        response_data["details"] = details
    
    return jsonify(response_data), status_code


def pagination_response(
    items: List[Any],
    total: int,
    page: int,
    per_page: int,
    message: str = "查询成功"
) -> tuple:
    """分页响应
    
    Args:
        items: 当前页数据列表
        total: 总记录数
        page: 当前页码（从1开始）
        per_page: 每页记录数
        message: 响应消息
        
    Returns:
        (response, status_code) 元组
    """
    total_pages = (total + per_page - 1) // per_page if per_page > 0 else 0
    
    data = {
        "items": items,
        "pagination": {
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": total_pages,
            "has_prev": page > 1,
            "has_next": page < total_pages
        }
    }
    
    return success_response(data=data, message=message)


def validation_error_response(
    errors: Dict[str, List[str]],
    message: str = "数据验证失败"
) -> tuple:
    """数据验证错误响应
    
    Args:
        errors: 字段错误字典，格式为 {字段名: [错误消息列表]}
        message: 响应消息
        
    Returns:
        (response, status_code) 元组
    """
    return error_response(
        message=message,
        status_code=422,
        details={"errors": errors}
    )


def make_response(
    success: bool,
    message: str,
    data: Optional[Any] = None,
    status_code: Optional[int] = None
) -> tuple:
    """通用响应生成器
    
    Args:
        success: 是否成功
        message: 响应消息
        data: 响应数据
        status_code: HTTP状态码，成功时默认200，失败时默认400
        
    Returns:
        (response, status_code) 元组
    """
    if success:
        return success_response(data=data, message=message, status_code=status_code or 200)
    else:
        return error_response(message=message, status_code=status_code or 400, data=data)


def api_response(func):
    """API响应装饰器
    
    将视图函数的返回值自动包装为标准响应格式。
    支持以下返回类型：
    1. (data, status_code)
    2. (data, message, status_code)
    3. 字典或列表（自动包装为成功响应）
    4. 元组 (success, message, data, status_code)
    
    Example:
        @api_response
        def get_items():
            items = Item.query.all()
            return items  # 自动包装为成功响应
            
        @api_response
        def create_item():
            if error:
                return False, "创建失败", None, 400
            return item, "创建成功", 201
    """
    from functools import wraps
    
    @wraps(func)
    def wrapper(*args, **kwargs):
        result = func(*args, **kwargs)
        
        # 如果已经是响应对象，直接返回
        if isinstance(result, tuple) and len(result) == 2:
            response, status_code = result
            if hasattr(response, 'get_json'):
                return response, status_code
        
        # 处理不同的返回类型
        if isinstance(result, tuple):
            if len(result) == 2:
                data, status_code = result
                if isinstance(status_code, int):
                    return success_response(data=data, status_code=status_code)
                else:
                    # 可能是 (data, message) 格式
                    return success_response(data=result[0], message=str(result[1]))
            elif len(result) == 3:
                data, message, status_code = result
                return success_response(data=data, message=str(message), status_code=status_code)
            elif len(result) == 4:
                success_flag, message, data, status_code = result
                if success_flag:
                    return success_response(data=data, message=str(message), status_code=status_code)
                else:
                    return error_response(message=str(message), status_code=status_code)
        elif isinstance(result, dict) or isinstance(result, list):
            return success_response(data=result)
        else:
            return success_response(data=result)
    
    return wrapper


# 导出常用函数
__all__ = [
    'success_response',
    'error_response',
    'pagination_response',
    'validation_error_response',
    'make_response',
    'api_response'
]