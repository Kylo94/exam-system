"""Flask应用工厂"""

from flask import Flask
from config import config

def create_app(config_name='default'):
    """
    创建Flask应用实例
    
    Args:
        config_name: 配置名称（development/testing/production）
        
    Returns:
        Flask应用实例
    """
    app = Flask(__name__)
    
    # 加载配置
    app.config.from_object(config[config_name])
    config[config_name].init_app(app)
    
    # 初始化扩展
    from .extensions import db, migrate, login_manager
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login_page'
    login_manager.login_message = '请先登录'
    login_manager.login_message_category = 'warning'
    
    # 注册蓝图
    register_blueprints(app)
    
    # 注册错误处理器
    register_error_handlers(app)
    
    # 注册上下文处理器
    register_context_processors(app)
    
    # 创建数据库表（开发环境）
    if app.config['DEBUG']:
        with app.app_context():
            # 导入模型以确保它们被注册
            from . import models
            db.create_all()
    
    return app


def register_blueprints(app: Flask):
    """注册所有蓝图"""
    from .routes import (
        main_bp,
        subjects_bp,
        levels_bp,
        exams_bp,
        questions_bp,
        submissions_bp,
        answers_bp,
        upload_bp,
        auth_bp
    )
    
    # 注册主蓝图（无前缀）
    app.register_blueprint(main_bp)
    
    # 注册认证蓝图
    app.register_blueprint(auth_bp, url_prefix='/auth')
    
    # 注册API蓝图
    app.register_blueprint(subjects_bp, url_prefix='/api')
    app.register_blueprint(levels_bp, url_prefix='/api')
    app.register_blueprint(exams_bp, url_prefix='/api')
    app.register_blueprint(questions_bp, url_prefix='/api')
    app.register_blueprint(submissions_bp, url_prefix='/api')
    app.register_blueprint(answers_bp, url_prefix='/api')
    app.register_blueprint(upload_bp, url_prefix='/api')


def register_error_handlers(app: Flask):
    """注册错误处理器"""
    from .utils.error_handlers import register_handlers
    register_handlers(app)


def register_context_processors(app: Flask):
    """注册上下文处理器"""
    from datetime import datetime, timezone
    
    @app.context_processor
    def inject_template_variables():
        """注入模板变量"""
        return {
            'app_name': app.config['APP_NAME'],
            'now': datetime.now(timezone.utc),
            'config': app.config
        }