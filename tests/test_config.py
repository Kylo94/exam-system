"""
配置模块测试
"""
import pytest
from app.config import settings, Settings


class TestSettings:
    """应用配置测试"""

    def test_settings_instance(self):
        """测试设置单例"""
        assert settings is not None
        assert isinstance(settings, Settings)

    def test_app_name_exists(self):
        """测试应用名称存在"""
        assert settings.APP_NAME is not None
        assert isinstance(settings.APP_NAME, str)

    def test_debug_is_bool(self):
        """测试调试模式是布尔值"""
        assert isinstance(settings.DEBUG, bool)

    def test_host_default(self):
        """测试默认主机"""
        assert settings.HOST == "0.0.0.0"

    def test_port_default(self):
        """测试默认端口"""
        assert settings.PORT == 8000

    def test_secret_key_exists(self):
        """测试密钥存在"""
        assert settings.SECRET_KEY is not None
        assert len(settings.SECRET_KEY) > 10

    def test_algorithm_default(self):
        """测试默认加密算法"""
        assert settings.ALGORITHM == "HS256"

    def test_token_expiry_positive(self):
        """测试令牌过期时间为正数"""
        assert settings.ACCESS_TOKEN_EXPIRE_MINUTES > 0

    def test_database_url_exists(self):
        """测试数据库URL存在"""
        assert settings.DATABASE_URL is not None
        assert len(settings.DATABASE_URL) > 0

    def test_admin_username_exists(self):
        """测试管理员用户名存在"""
        assert settings.ADMIN_USERNAME is not None
        assert len(settings.ADMIN_USERNAME) > 0

    def test_admin_email_format(self):
        """测试管理员邮箱格式"""
        assert "@" in settings.ADMIN_EMAIL

    def test_upload_folder_exists(self):
        """测试上传文件夹配置存在"""
        assert settings.UPLOAD_FOLDER is not None
        assert len(settings.UPLOAD_FOLDER) > 0

    def test_max_content_length_positive(self):
        """测试最大内容长度为正数"""
        assert settings.MAX_CONTENT_LENGTH > 0

    def test_settings_case_sensitive(self):
        """测试配置大小写敏感"""
        s = Settings()
        assert hasattr(s, 'APP_NAME')
        assert not hasattr(s, 'app_name')

    def test_extra_fields_ignored(self):
        """测试忽略额外字段"""
        # 应该不抛出异常
        s = Settings(NONEXISTENT_FIELD="value")
        assert not hasattr(s, 'NONEXISTENT_FIELD')