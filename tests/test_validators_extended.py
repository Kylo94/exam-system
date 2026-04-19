"""
扩展验证器测试 - 日期、日期时间、手机号、文件扩展名
"""
import pytest
from app.utils.validators import (
    validate_date,
    validate_datetime,
    validate_phone,
    validate_file_extension,
)


class TestValidateDate:
    """日期验证测试"""

    def test_valid_date(self):
        """测试有效日期"""
        is_valid, error = validate_date("2024-01-15")
        assert is_valid is True
        assert error is None

    def test_valid_date_custom_format(self):
        """测试自定义格式日期"""
        is_valid, error = validate_date("15/01/2024", format="%d/%m/%Y")
        assert is_valid is True
        assert error is None

    def test_invalid_date_format(self):
        """测试无效日期格式"""
        is_valid, error = validate_date("2024-13-45")
        assert is_valid is False
        assert "格式不正确" in error

    def test_invalid_date_wrong_format(self):
        """测试格式不匹配"""
        is_valid, error = validate_date("2024-01-15", format="%d/%m/%Y")
        assert is_valid is False

    def test_none_not_allowed(self):
        """测试None不允许"""
        is_valid, error = validate_date(None)
        assert is_valid is False
        assert "不能为空" in error

    def test_none_allowed(self):
        """测试None允许"""
        is_valid, error = validate_date(None, allow_none=True)
        assert is_valid is True
        assert error is None

    def test_not_string(self):
        """测试非字符串"""
        is_valid, error = validate_date(20240115)
        assert is_valid is False
        assert "必须是字符串类型" in error


class TestValidateDatetime:
    """日期时间验证测试"""

    def test_valid_datetime(self):
        """测试有效日期时间"""
        is_valid, error = validate_datetime("2024-01-15 10:30:00")
        assert is_valid is True
        assert error is None

    def test_valid_datetime_custom_format(self):
        """测试自定义格式日期时间"""
        is_valid, error = validate_datetime("15-01-2024 10:30", format="%d-%m-%Y %H:%M")
        assert is_valid is True

    def test_invalid_datetime(self):
        """测试无效日期时间"""
        is_valid, error = validate_datetime("2024-13-45 99:99:99")
        assert is_valid is False
        assert "格式不正确" in error

    def test_none_not_allowed(self):
        """测试None不允许"""
        is_valid, error = validate_datetime(None)
        assert is_valid is False

    def test_none_allowed(self):
        """测试None允许"""
        is_valid, error = validate_datetime(None, allow_none=True)
        assert is_valid is True


class TestValidatePhone:
    """手机号验证测试"""

    def test_valid_phone(self):
        """测试有效手机号"""
        is_valid, error = validate_phone("13812345678")
        assert is_valid is True
        assert error is None

    def test_valid_phone_2(self):
        """测试有效手机号2"""
        is_valid, error = validate_phone("19912345678")
        assert is_valid is True

    def test_valid_phone_3(self):
        """测试有效手机号（联通）"""
        is_valid, error = validate_phone("18612345678")
        assert is_valid is True

    def test_invalid_phone_too_short(self):
        """测试过短手机号"""
        is_valid, error = validate_phone("1381234567")
        assert is_valid is False
        assert "格式不正确" in error

    def test_invalid_phone_wrong_prefix(self):
        """测试错误前缀手机号"""
        is_valid, error = validate_phone("12812345678")
        assert is_valid is False

    def test_invalid_phone_letters(self):
        """测试包含字母手机号"""
        is_valid, error = validate_phone("1381234567a")
        assert is_valid is False

    def test_none_not_allowed(self):
        """测试None不允许"""
        is_valid, error = validate_phone(None)
        assert is_valid is False

    def test_none_allowed(self):
        """测试None允许"""
        is_valid, error = validate_phone(None, allow_none=True)
        assert is_valid is True

    def test_not_string(self):
        """测试非字符串"""
        is_valid, error = validate_phone(13812345678)
        assert is_valid is False


class TestValidateFileExtension:
    """文件扩展名验证测试"""

    def test_valid_extension_docx(self):
        """测试有效扩展名docx"""
        is_valid, error = validate_file_extension("document.docx", [".docx", ".pdf", ".txt"])
        assert is_valid is True
        assert error is None

    def test_valid_extension_pdf(self):
        """测试有效扩展名pdf"""
        is_valid, error = validate_file_extension("file.PDF", [".docx", ".pdf", ".txt"])
        assert is_valid is True

    def test_valid_extension_no_dot(self):
        """测试有扩展名但无点号"""
        is_valid, error = validate_file_extension("documentdocx", [".docx"])
        assert is_valid is False
        assert "没有扩展名" in error

    def test_invalid_extension(self):
        """测试无效扩展名"""
        is_valid, error = validate_file_extension("script.exe", [".docx", ".pdf", ".txt"])
        assert is_valid is False
        assert "只支持以下格式" in error

    def test_none_not_allowed(self):
        """测试None不允许"""
        is_valid, error = validate_file_extension(None, [".docx"])
        assert is_valid is False

    def test_none_allowed(self):
        """测试None允许"""
        is_valid, error = validate_file_extension(None, [".docx"], allow_none=True)
        assert is_valid is True

    def test_not_string(self):
        """测试非字符串"""
        is_valid, error = validate_file_extension(123, [".docx"])
        assert is_valid is False