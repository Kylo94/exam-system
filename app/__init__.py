"""Flask应用工厂"""

import os
from flask import Flask
from config import config

# 全局初始化标记，防止多进程重复初始化
_app_initialized = False

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

    # 应用启动时的初始化检查（只在第一个 worker 执行）
    with app.app_context():
        initialize_app(app)

    return app


def initialize_app(app):
    """
    应用启动初始化
    检查数据库完整性并自动初始化
    """
    from .extensions import db
    from .models.user import User
    from flask_migrate import upgrade
    import logging
    import os

    global _app_initialized
    if _app_initialized:
        app.logger.info('应用已初始化，跳过重复检查')
        return

    app.logger.info('开始应用初始化检查...')

    # 确保 instance 目录存在
    db_uri = app.config.get('SQLALCHEMY_DATABASE_URI', '')
    if db_uri.startswith('sqlite:///'):
        # 处理三种 SQLite 路径格式
        # sqlite:///file.db -> file.db
        # sqlite:////absolute/path.db -> /absolute/path.db
        # sqlite://relative/path.db -> relative/path.db
        db_path = db_uri.replace('sqlite:///', '')
        if db_path.startswith('/'):
            # 绝对路径: sqlite:////absolute/path
            db_path = db_path.lstrip('/')
        db_dir = os.path.dirname(db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)
            app.logger.info(f'✓ 创建数据库目录: {db_dir}')

    try:
        # 1. 检查数据库连接
        db.engine.connect()
        app.logger.info('✓ 数据库连接正常')

        # 2. 检查数据库表结构，执行迁移
        try:
            from alembic.config import Config
            from alembic import command
            import os

            # 检查是否是全新数据库（没有 alembic_version 表）
            inspector = db.inspect(db.engine)
            try:
                tables = list(inspector.get_table_names()) if inspector.get_table_names() else []
            except:
                tables = []

            if 'alembic_version' not in tables:
                # 全新数据库，使用 db.create_all() 创建所有表
                app.logger.info('检测到全新数据库，正在创建表结构...')
                db.create_all()
                # 标记迁移为最新版本
                config = Config()
                config.set_main_option('sqlalchemy.url', str(db.engine.url))
                config.set_main_option('script_location', os.path.join(os.path.dirname(__file__), '..', 'migrations'))
                command.stamp(config, 'head')
                app.logger.info('✓ 数据库表创建完成')
            else:
                # 已有数据库，执行增量迁移
                upgrade()
                app.logger.info('✓ 数据库迁移完成')
        except Exception as e:
            app.logger.warning(f'数据库迁移警告: {e}')

        # 3. 检查管理员账户，不存在则创建
        create_admin_if_not_exists(app)

        _app_initialized = True

    except Exception as e:
        app.logger.error(f'数据库初始化失败: {e}')
        raise


def create_admin_if_not_exists(app):
    """创建管理员账户（如果不存在）"""
    from .models.user import User
    from .extensions import db
    import os

    admin_username = os.environ.get('ADMIN_USERNAME', 'admin')
    admin_password = os.environ.get('ADMIN_PASSWORD', 'admin')
    admin_email = os.environ.get('ADMIN_EMAIL', 'admin@example.com')

    try:
        existing_admin = User.get_by_username(admin_username)
        if existing_admin:
            app.logger.info(f'✓ 管理员用户已存在: {admin_username}')
            return

        # 检查邮箱是否被占用
        existing_email = User.get_by_email(admin_email)
        if existing_email:
            app.logger.warning(f'邮箱 {admin_email} 已被占用，使用备用邮箱')
            admin_email = f'{admin_username}@system.local'

        admin = User(
            username=admin_username,
            email=admin_email,
            password=admin_password,
            role='admin',
            is_active=True
        )
        db.session.add(admin)
        db.session.commit()

        app.logger.info(f'✓ 管理员用户创建成功: {admin_username}')
        app.logger.info(f'  邮箱: {admin_email}')

    except Exception as e:
        db.session.rollback()
        app.logger.error(f'创建管理员失败: {e}')
        raise


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