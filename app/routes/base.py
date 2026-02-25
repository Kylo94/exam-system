"""基础路由类

提供路由的通用功能，如参数验证、响应格式化等。
"""

from typing import Any, Dict, List, Optional, Union
from flask import request, jsonify, current_app
from flask.views import MethodView
from werkzeug.exceptions import BadRequest
from sqlalchemy.exc import IntegrityError

from app.utils.error_handlers import (
    APIError, ValidationError, NotFoundError,
    AuthenticationError, AuthorizationError
)


class BaseResource(MethodView):
    """基础资源类，所有路由资源的基类"""
    
    # 服务类，子类需要设置
    service_class = None
    
    def __init__(self):
        """初始化资源"""
        if self.service_class:
            self.service = self.service_class(current_app.extensions['sqlalchemy'])
        else:
            self.service = None
    
    def get_service(self):
        """获取服务实例"""
        if not self.service and self.service_class:
            self.service = self.service_class(current_app.extensions['sqlalchemy'])
        return self.service
    
    def parse_request_json(self, required_fields: Optional[List[str]] = None) -> Dict[str, Any]:
        """解析请求JSON数据
        
        Args:
            required_fields: 必填字段列表
            
        Returns:
            解析后的数据字典
            
        Raises:
            BadRequest: 请求格式错误
            ValidationError: 缺少必填字段
        """
        try:
            data = request.get_json()
        except Exception:
            raise BadRequest("请求必须是有效的JSON格式")
        
        if data is None:
            raise BadRequest("请求必须包含JSON数据")
        
        if required_fields:
            missing_fields = [field for field in required_fields if field not in data]
            if missing_fields:
                raise ValidationError(f"缺少必填字段: {', '.join(missing_fields)}")
        
        return data
    
    def parse_query_params(self) -> Dict[str, Any]:
        """解析查询参数
        
        Returns:
            查询参数字典
        """
        params = {}
        
        # 分页参数
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        if page < 1:
            page = 1
        if per_page < 1:
            per_page = 20
        if per_page > 100:
            per_page = 100
        
        params['page'] = page
        params['per_page'] = per_page
        params['skip'] = (page - 1) * per_page
        params['limit'] = per_page
        
        # 排序参数
        sort_by = request.args.get('sort_by')
        sort_order = request.args.get('sort_order', 'asc')
        if sort_by:
            params['sort_by'] = sort_by
            params['sort_order'] = sort_order if sort_order in ['asc', 'desc'] else 'asc'
        
        # 搜索参数
        search = request.args.get('search')
        if search:
            params['search'] = search
        
        # 过滤参数（除分页、排序、搜索外的所有参数）
        for key, value in request.args.items():
            if key not in ['page', 'per_page', 'sort_by', 'sort_order', 'search']:
                params[key] = value
        
        return params
    
    def success_response(self, data: Any = None, message: str = "成功", 
                        status_code: int = 200) -> tuple:
        """构建成功响应
        
        Args:
            data: 响应数据
            message: 成功消息
            status_code: HTTP状态码
            
        Returns:
            (响应JSON, 状态码) 元组
        """
        response = {
            'success': True,
            'message': message,
            'data': data
        }
        return jsonify(response), status_code
    
    def error_response(self, error: Exception, status_code: int = 400) -> tuple:
        """构建错误响应
        
        Args:
            error: 异常对象
            status_code: HTTP状态码
            
        Returns:
            (响应JSON, 状态码) 元组
        """
        response = {
            'success': False,
            'message': str(error),
            'error_type': error.__class__.__name__
        }
        
        # 添加额外信息
        if hasattr(error, 'details'):
            response['details'] = error.details
        
        return jsonify(response), status_code
    
    def paginated_response(self, items: List[Any], total: int, 
                          page: int, per_page: int) -> tuple:
        """构建分页响应
        
        Args:
            items: 当前页数据
            total: 总记录数
            page: 当前页码
            per_page: 每页记录数
            
        Returns:
            (响应JSON, 状态码) 元组
        """
        total_pages = (total + per_page - 1) // per_page if per_page > 0 else 0
        
        pagination = {
            'page': page,
            'per_page': per_page,
            'total': total,
            'total_pages': total_pages,
            'has_prev': page > 1,
            'has_next': page < total_pages
        }
        
        data = {
            'items': items,
            'pagination': pagination
        }
        
        return self.success_response(data)
    
    def handle_exception(self, error: Exception):
        """处理异常
        
        Args:
            error: 异常对象
        """
        # 记录异常信息
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"处理请求时发生异常: {error}", exc_info=True)
        
        # 根据异常类型设置状态码
        if isinstance(error, BadRequest):
            status_code = 400
        elif isinstance(error, ValidationError):
            status_code = 400
        elif isinstance(error, AuthenticationError):
            status_code = 401
        elif isinstance(error, AuthorizationError):
            status_code = 403
        elif isinstance(error, NotFoundError):
            status_code = 404
        elif isinstance(error, APIError):
            status_code = error.status_code
        elif isinstance(error, IntegrityError):
            # 数据库完整性错误，通常是唯一约束冲突
            status_code = 400
            # 提取更友好的错误信息
            error_msg = str(error.orig) if hasattr(error, 'orig') and error.orig else "数据冲突，可能已存在相同记录"
            # 检查是否是唯一约束冲突
            if "UNIQUE constraint failed" in error_msg or "duplicate key" in error_msg:
                error_msg = "数据已存在，请勿重复添加"
            # 创建一个新的错误对象，使用已经导入的ValidationError
            error = ValidationError(f"数据验证失败: {error_msg}")
        else:
            status_code = 500
            # 生产环境下隐藏内部错误细节
            if not current_app.config.get('DEBUG', False):
                return jsonify({
                    'success': False,
                    'message': '服务器内部错误',
                    'error_type': 'InternalServerError'
                }), 500
        
        return self.error_response(error, status_code)