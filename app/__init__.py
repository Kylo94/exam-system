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
    app = Flask(__name__, 
                template_folder='../templates',
                static_folder='../static')
    
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
    
    # 开发环境额外配置
    if app.config['DEBUG']:
        # 禁用模板缓存
        app.config['TEMPLATES_AUTO_RELOAD'] = True
        app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
    
    return app


def register_blueprints(app: Flask):
    """注册所有蓝图"""
    from .routes import (
        main_bp,
        subjects_bp,
        levels_bp,
        knowledge_points_bp,
        exams_bp,
        questions_bp,
        submissions_bp,
        answers_bp,
        upload_bp,
        auth_bp,
        admin_bp,
        teacher_bp,
        teacher_api_bp,
        ai_configs_bp,
        document_parser_bp,
        student_bp
    )

    # 注册主蓝图（无前缀）
    app.register_blueprint(main_bp)

    # 注册认证蓝图
    app.register_blueprint(auth_bp, url_prefix='/auth')

    # 注册管理蓝图
    app.register_blueprint(admin_bp, url_prefix='/admin')

    # 注册教师蓝图
    app.register_blueprint(teacher_bp, url_prefix='/teacher')

    # 注册学生蓝图
    app.register_blueprint(student_bp, url_prefix='/student')

    # 注册API蓝图
    app.register_blueprint(subjects_bp, url_prefix='/api')
    app.register_blueprint(levels_bp, url_prefix='/api')
    app.register_blueprint(knowledge_points_bp, url_prefix='/api')
    app.register_blueprint(exams_bp, url_prefix='/api')
    app.register_blueprint(questions_bp, url_prefix='/api')
    app.register_blueprint(submissions_bp, url_prefix='/api')
    app.register_blueprint(answers_bp, url_prefix='/api')
    app.register_blueprint(upload_bp, url_prefix='/api')
    app.register_blueprint(ai_configs_bp, url_prefix='/api')
    app.register_blueprint(document_parser_bp, url_prefix='/api')
    app.register_blueprint(teacher_api_bp)


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