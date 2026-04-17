"""
验证器单元测试
"""
import pytest
from app.utils.validators import (
    validate_string,
    validate_integer,
    validate_number,
    validate_email,
    validate_phone,
    validate_url,
    validate_username,
    validate_password,
    validate_choice,
    validate_list,
    validate_dict,
    validate_json,
    validate_file_extension,
    batch_validate
)


class TestValidateString:
    """字符串验证测试"""

    def test_valid_string(self):
        is_valid, error = validate_string("hello", field_name="名称")
        assert is_valid is True
        assert error is None

    def test_none_not_allowed(self):
        is_valid, error = validate_string(None, field_name="名称")
        assert is_valid is False
        assert "不能为空" in error

    def test_none_allowed(self):
        is_valid, error = validate_string(None, field_name="名称", allow_none=True)
        assert is_valid is True

    def test_empty_not_allowed(self):
        is_valid, error = validate_string("", field_name="名称", allow_empty=False)
        assert is_valid is False
        assert "不能为空" in error

    def test_min_length(self):
        is_valid, error = validate_string("ab", field_name="名称", min_length=3)
        assert is_valid is False
        assert "长度不能小于" in error

    def test_max_length(self):
        is_valid, error = validate_string("abcde", field_name="名称", max_length=3)
        assert is_valid is False
        assert "长度不能超过" in error

    def test_not_string_type(self):
        is_valid, error = validate_string(123, field_name="名称")
        assert is_valid is False
        assert "必须是字符串类型" in error


class TestValidateInteger:
    """整数验证测试"""

    def test_valid_integer(self):
        is_valid, error = validate_integer(42, field_name="年龄")
        assert is_valid is True

    def test_string_integer(self):
        is_valid, error = validate_integer("42", field_name="年龄")
        assert is_valid is True

    def test_float_becomes_integer(self):
        # validate_integer 使用 int() 转换，所以 float 可以通过
        is_valid, error = validate_integer(3.14, field_name="年龄")
        # 3.14 -> int(3.14) = 3，可以验证通过
        assert is_valid is True

    def test_min_value(self):
        is_valid, error = validate_integer(5, field_name="年龄", min_value=18)
        assert is_valid is False
        assert "不能小于" in error

    def test_max_value(self):
        is_valid, error = validate_integer(150, field_name="年龄", max_value=120)
        assert is_valid is False
        assert "不能大于" in error

    def test_none_allowed(self):
        is_valid, error = validate_integer(None, field_name="年龄", allow_none=True)
        assert is_valid is True


class TestValidateNumber:
    """数字验证测试"""

    def test_valid_integer(self):
        is_valid, error = validate_number(42)
        assert is_valid is True

    def test_valid_float(self):
        is_valid, error = validate_number(3.14)
        assert is_valid is True

    def test_string_number(self):
        is_valid, error = validate_number("3.14")
        assert is_valid is True

    def test_invalid_number(self):
        is_valid, error = validate_number("abc")
        assert is_valid is False


class TestValidateEmail:
    """邮箱验证测试"""

    def test_valid_email(self):
        is_valid, error = validate_email("user@example.com")
        assert is_valid is True

    def test_valid_email_with_subdomain(self):
        is_valid, error = validate_email("user@mail.example.com")
        assert is_valid is True

    def test_invalid_email_no_at(self):
        is_valid, error = validate_email("userexample.com")
        assert is_valid is False
        assert "格式不正确" in error

    def test_invalid_email_no_domain(self):
        is_valid, error = validate_email("user@")
        assert is_valid is False

    def test_none_allowed(self):
        is_valid, error = validate_email(None, allow_none=True)
        assert is_valid is True


class TestValidatePhone:
    """手机号验证测试"""

    def test_valid_phone(self):
        is_valid, error = validate_phone("13812345678")
        assert is_valid is True

    def test_valid_phone_2(self):
        is_valid, error = validate_phone("19912345678")
        assert is_valid is True

    def test_invalid_phone_short(self):
        is_valid, error = validate_phone("1381234567")
        assert is_valid is False

    def test_invalid_phone_wrong_prefix(self):
        is_valid, error = validate_phone("12812345678")
        assert is_valid is False


class TestValidateURL:
    """URL验证测试"""

    def test_valid_http_url(self):
        is_valid, error = validate_url("http://example.com")
        assert is_valid is True

    def test_valid_https_url(self):
        is_valid, error = validate_url("https://example.com/page")
        assert is_valid is True

    def test_valid_url_with_port(self):
        is_valid, error = validate_url("http://localhost:8080")
        assert is_valid is True

    def test_invalid_url(self):
        is_valid, error = validate_url("not a url")
        assert is_valid is False

    def test_require_https(self):
        is_valid, error = validate_url("http://example.com", require_https=True)
        assert is_valid is False
        assert "HTTPS" in error


class TestValidateUsername:
    """用户名验证测试"""

    def test_valid_username(self):
        is_valid, error = validate_username("john_doe")
        assert is_valid is True

    def test_valid_username_letters(self):
        is_valid, error = validate_username("john")
        assert is_valid is True

    def test_valid_username_numbers(self):
        is_valid, error = validate_username("user123")
        assert is_valid is True

    def test_invalid_username_too_short(self):
        is_valid, error = validate_username("ab")
        assert is_valid is False
        assert "3-20位" in error

    def test_invalid_username_special_chars(self):
        is_valid, error = validate_username("user@name")
        assert is_valid is False


class TestValidatePassword:
    """密码验证测试"""

    def test_valid_password(self):
        is_valid, error = validate_password("password123")
        assert is_valid is True

    def test_invalid_password_too_short(self):
        is_valid, error = validate_password("12345")
        assert is_valid is False
        assert "6-50位" in error

    def test_invalid_password_too_long(self):
        is_valid, error = validate_password("a" * 51)
        assert is_valid is False


class TestValidateChoice:
    """选项验证测试"""

    def test_valid_choice(self):
        is_valid, error = validate_choice("A", ["A", "B", "C"])
        assert is_valid is True

    def test_invalid_choice(self):
        is_valid, error = validate_choice("D", ["A", "B", "C"])
        assert is_valid is False
        assert "必须是以下值之一" in error


class TestValidateList:
    """列表验证测试"""

    def test_valid_list(self):
        is_valid, error = validate_list([1, 2, 3])
        assert is_valid is True

    def test_empty_not_allowed(self):
        is_valid, error = validate_list([], allow_empty=False)
        assert is_valid is False
        assert "不能为空" in error

    def test_min_length(self):
        is_valid, error = validate_list([1], min_length=2)
        assert is_valid is False

    def test_not_list_type(self):
        is_valid, error = validate_list("not a list")
        assert is_valid is False


class TestValidateDict:
    """字典验证测试"""

    def test_valid_dict(self):
        is_valid, error = validate_dict({"key": "value"})
        assert is_valid is True

    def test_required_keys(self):
        is_valid, error = validate_dict({"a": 1}, required_keys=["a", "b"])
        assert is_valid is False
        assert "b" in error

    def test_all_required_keys_present(self):
        is_valid, error = validate_dict({"a": 1, "b": 2}, required_keys=["a", "b"])
        assert is_valid is True


class TestValidateJSON:
    """JSON验证测试"""

    def test_valid_json(self):
        is_valid, error = validate_json('{"key": "value"}')
        assert is_valid is True

    def test_valid_json_array(self):
        is_valid, error = validate_json('[1, 2, 3]')
        assert is_valid is True

    def test_invalid_json(self):
        is_valid, error = validate_json("{key: value}")
        assert is_valid is False
        assert "JSON" in error


class TestValidateFileExtension:
    """文件扩展名验证测试"""

    def test_valid_extension(self):
        is_valid, error = validate_file_extension("image.jpg", [".jpg", ".png"])
        assert is_valid is True

    def test_invalid_extension(self):
        is_valid, error = validate_file_extension("doc.pdf", [".jpg", ".png"])
        assert is_valid is False
        assert "只支持以下格式" in error

    def test_no_extension(self):
        is_valid, error = validate_file_extension("noextension", [".jpg"])
        assert is_valid is False
        assert "没有扩展名" in error


class TestBatchValidate:
    """批量验证测试"""

    def test_batch_valid(self):
        validators = {
            "username": (validate_username, {}),
            "email": (validate_email, {}),
            "age": (validate_integer, {"min_value": 0})
        }
        data = {"username": "john", "email": "john@test.com", "age": 25}
        
        errors = batch_validate(validators, data)
        
        assert errors == {}

    def test_batch_with_errors(self):
        validators = {
            "username": (validate_username, {}),
            "email": (validate_email, {})
        }
        data = {"username": "ab", "email": "invalid"}
        
        errors = batch_validate(validators, data)
        
        assert "username" in errors
        assert "email" in errors
