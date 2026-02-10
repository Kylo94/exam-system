"""统一错误处理模块"""

import logging
from typing import Dict, Any, Optional
from flask import jsonify, request
from werkzeug.exceptions import HTTPException


class APIError(Exception):
    """
    基础API异常类
    
    Attributes:
        message: 错误信息
        status_code: HTTP状态码
        code: 业务错误码
        details: 错误详情
    """
    
    def __init__(
        self,
        message: str,
        status_code: int = 400,
        code: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.code = code or status_code
        self.details = details or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'error': {
                'message': self.message,
                'code': self.code,
                'details': self.details,
            }
        }


class ValidationError(APIError):
    """数据验证错误"""
    
    def __init__(
        self,
        message: str = '数据验证失败',
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, 400, 1001, details)


class NotFoundError(APIError):
    """资源未找到错误"""
    
    def __init__(
        self,
        message: str = '请求的资源不存在',
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, 404, 1002, details)


class AuthenticationError(APIError):
    """认证失败错误"""
    
    def __init__(
        self,
        message: str = '认证失败',
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, 401, 1003, details)


class AuthorizationError(APIError):
    """授权失败错误"""
    
    def __init__(
        self,
        message: str = '没有访问权限',
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, 403, 1004, details)


def register_handlers(app):
    """
    注册错误处理器
    
    Args:
        app: Flask应用实例
    """
    
    @app.errorhandler(APIError)
    def handle_api_error(error: APIError):
        """处理APIError异常"""
        response = jsonify(error.to_dict())
        response.status_code = error.status_code
        return response
    
    @app.errorhandler(HTTPException)
    def handle_http_error(error: HTTPException):
        """处理HTTPException异常"""
        response = jsonify({
            'error': {
                'message': error.description or 'HTTP错误',
                'code': error.code,
                'details': {},
            }
        })
        response.status_code = error.code
        return response
    
    @app.errorhandler(Exception)
    def handle_generic_error(error: Exception):
        """处理其他未捕获异常"""
        # 记录错误日志
        app.logger.error(f'未捕获异常: {str(error)}', exc_info=True)
        
        # 生产环境返回通用错误信息
        if not app.config['DEBUG']:
            response = jsonify({
                'error': {
                    'message': '服务器内部错误',
                    'code': 500,
                    'details': {},
                }
            })
            response.status_code = 500
            return response
        
        # 开发环境返回详细错误信息
        import traceback
        response = jsonify({
            'error': {
                'message': str(error),
                'code': 500,
                'details': {
                    'traceback': traceback.format_exc().split('\n')
                },
            }
        })
        response.status_code = 500
        return response
    
    # 添加请求日志
    @app.before_request
    def log_request_info():
        """记录请求信息"""
        if app.config['DEBUG']:
            app.logger.debug(f'请求: {request.method} {request.path}')
    
    @app.after_request
    def add_cors_headers(response):
        """添加CORS头以支持跨域请求"""
        # 允许所有来源（开发环境）
        response.headers['Access-Control-Allow-Origin'] = request.headers.get('Origin', '*')
        response.headers['Access-Control-Allow-Credentials'] = 'true'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS, PATCH'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-Requested-With'
        
        # 记录响应信息
        if app.config['DEBUG']:
            app.logger.debug(f'响应: {response.status_code}')
        
        return response