"""
认证功能单元测试
"""
import pytest
from datetime import timedelta

from app.auth import (
    verify_password,
    get_password_hash,
    create_access_token,
    decode_token,
    require_role
)


class TestPasswordHashing:
    """密码哈希测试"""

    def test_password_hash_creates_hash(self):
        """测试密码哈希生成"""
        password = "secure_password_123"
        hashed = get_password_hash(password)
        
        assert hashed is not None
        assert hashed != password
        assert len(hashed) > 20

    def test_password_hash_different_each_time(self):
        """测试每次哈希结果不同（加盐）"""
        password = "same_password"
        hash1 = get_password_hash(password)
        hash2 = get_password_hash(password)
        
        # bcrypt使用随机盐，每次哈希结果不同
        assert hash1 != hash2

    def test_verify_password_correct(self):
        """测试正确密码验证"""
        password = "correct_password"
        hashed = get_password_hash(password)
        
        assert verify_password(password, hashed) is True

    def test_verify_password_incorrect(self):
        """测试错误密码验证"""
        password = "correct_password"
        wrong_password = "wrong_password"
        hashed = get_password_hash(password)
        
        assert verify_password(wrong_password, hashed) is False

    def test_verify_empty_password(self):
        """测试空密码验证"""
        hashed = get_password_hash("password")
        
        assert verify_password("", hashed) is False

    def test_verify_special_characters(self):
        """测试特殊字符密码"""
        password = "密码123!@#$%^&*()"
        hashed = get_password_hash(password)
        
        assert verify_password(password, hashed) is True


class TestJWTToken:
    """JWT令牌测试"""

    def test_create_access_token(self):
        """测试创建访问令牌"""
        data = {"sub": "12345", "role": "student"}
        token = create_access_token(data)
        
        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 50

    def test_create_token_with_expiry(self):
        """测试带过期时间的令牌"""
        data = {"sub": "12345"}
        expires = timedelta(minutes=30)
        token = create_access_token(data, expires_delta=expires)
        
        assert token is not None

    def test_decode_valid_token(self):
        """测试解码有效令牌"""
        data = {"sub": "12345", "role": "admin"}
        token = create_access_token(data)
        
        payload = decode_token(token)
        
        assert payload is not None
        assert payload["sub"] == "12345"
        assert payload["role"] == "admin"
        assert "exp" in payload

    def test_decode_invalid_token(self):
        """测试解码无效令牌"""
        invalid_token = "invalid.token.here"
        
        payload = decode_token(invalid_token)
        
        assert payload is None

    def test_decode_tampered_token(self):
        """测试解码篡改的令牌"""
        data = {"sub": "12345"}
        token = create_access_token(data)
        
        # 篡改令牌最后几个字符
        tampered = token[:-5] + "xxxxx"
        
        payload = decode_token(tampered)
        
        assert payload is None


class TestRoleChecker:
    """角色检查器测试"""

    def test_require_role_decorator(self):
        """测试角色装饰器"""
        # 这个需要模拟FastAPI依赖注入，比较复杂
        # 这里只测试装饰器本身的行为
        checker = require_role("admin", "teacher")
        
        assert callable(checker)
