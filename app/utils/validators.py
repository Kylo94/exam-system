"""数据验证工具模块

提供通用的数据验证函数，确保输入数据的完整性和正确性。
"""

import re
import json
from typing import Any, Dict, List, Optional, Tuple, Union
from datetime import datetime
from urllib.parse import urlparse


# 常用正则表达式
EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
URL_REGEX = re.compile(
    r'^(https?://)?'  # 协议
    r'(([a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}|'  # 域名
    r'localhost|'  # localhost
    r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # IP地址
    r'(:\d+)?'  # 端口
    r'(/.*)?$'  # 路径
)
PHONE_REGEX = re.compile(r'^1[3-9]\d{9}$')  # 中国大陆手机号
USERNAME_REGEX = re.compile(r'^[a-zA-Z0-9_]{3,20}$')
PASSWORD_REGEX = re.compile(r'^.{6,50}$')  # 6-50位任意字符


def validate_string(
    value: Any,
    field_name: str = "字段",
    min_length: int = 0,
    max_length: Optional[int] = None,
    allow_empty: bool = True,
    allow_none: bool = False
) -> Tuple[bool, Optional[str]]:
    """验证字符串
    
    Args:
        value: 待验证的值
        field_name: 字段名称，用于错误消息
        min_length: 最小长度
        max_length: 最大长度
        allow_empty: 是否允许空字符串
        allow_none: 是否允许None值
        
    Returns:
        (是否有效, 错误消息)
    """
    if value is None:
        if allow_none:
            return True, None
        return False, f"{field_name}不能为空"
    
    if not isinstance(value, str):
        return False, f"{field_name}必须是字符串类型"
    
    if not allow_empty and value == "":
        return False, f"{field_name}不能为空"
    
    if len(value) < min_length:
        return False, f"{field_name}长度不能小于{min_length}个字符"
    
    if max_length is not None and len(value) > max_length:
        return False, f"{field_name}长度不能超过{max_length}个字符"
    
    return True, None


def validate_integer(
    value: Any,
    field_name: str = "字段",
    min_value: Optional[int] = None,
    max_value: Optional[int] = None,
    allow_none: bool = False
) -> Tuple[bool, Optional[str]]:
    """验证整数
    
    Args:
        value: 待验证的值
        field_name: 字段名称
        min_value: 最小值
        max_value: 最大值
        allow_none: 是否允许None值
        
    Returns:
        (是否有效, 错误消息)
    """
    if value is None:
        if allow_none:
            return True, None
        return False, f"{field_name}不能为空"
    
    try:
        int_value = int(value)
    except (ValueError, TypeError):
        return False, f"{field_name}必须是整数"
    
    if min_value is not None and int_value < min_value:
        return False, f"{field_name}不能小于{min_value}"
    
    if max_value is not None and int_value > max_value:
        return False, f"{field_name}不能大于{max_value}"
    
    return True, None


def validate_number(
    value: Any,
    field_name: str = "字段",
    min_value: Optional[Union[int, float]] = None,
    max_value: Optional[Union[int, float]] = None,
    allow_none: bool = False
) -> Tuple[bool, Optional[str]]:
    """验证数字（整数或浮点数）
    
    Args:
        value: 待验证的值
        field_name: 字段名称
        min_value: 最小值
        max_value: 最大值
        allow_none: 是否允许None值
        
    Returns:
        (是否有效, 错误消息)
    """
    if value is None:
        if allow_none:
            return True, None
        return False, f"{field_name}不能为空"
    
    try:
        num_value = float(value)
    except (ValueError, TypeError):
        return False, f"{field_name}必须是数字"
    
    if min_value is not None and num_value < min_value:
        return False, f"{field_name}不能小于{min_value}"
    
    if max_value is not None and num_value > max_value:
        return False, f"{field_name}不能大于{max_value}"
    
    return True, None


def validate_email(
    email: Any,
    field_name: str = "邮箱",
    allow_none: bool = False
) -> Tuple[bool, Optional[str]]:
    """验证邮箱地址
    
    Args:
        email: 待验证的邮箱地址
        field_name: 字段名称
        allow_none: 是否允许None值
        
    Returns:
        (是否有效, 错误消息)
    """
    if email is None:
        if allow_none:
            return True, None
        return False, f"{field_name}不能为空"
    
    if not isinstance(email, str):
        return False, f"{field_name}必须是字符串类型"
    
    if EMAIL_REGEX.match(email):
        return True, None
    else:
        return False, f"{field_name}格式不正确"


def validate_url(
    url: Any,
    field_name: str = "URL",
    require_https: bool = False,
    allow_none: bool = False
) -> Tuple[bool, Optional[str]]:
    """验证URL
    
    Args:
        url: 待验证的URL
        field_name: 字段名称
        require_https: 是否要求HTTPS协议
        allow_none: 是否允许None值
        
    Returns:
        (是否有效, 错误消息)
    """
    if url is None:
        if allow_none:
            return True, None
        return False, f"{field_name}不能为空"
    
    if not isinstance(url, str):
        return False, f"{field_name}必须是字符串类型"
    
    if not url:
        return False, f"{field_name}不能为空"
    
    # 使用正则表达式初步验证
    if not URL_REGEX.match(url):
        return False, f"{field_name}格式不正确"
    
    # 进一步使用urlparse验证
    try:
        parsed = urlparse(url)
        if not parsed.scheme and not parsed.netloc:
            # 如果没有协议和网络位置，尝试添加http://
            parsed = urlparse(f"http://{url}")
        
        if not parsed.netloc:
            return False, f"{field_name}缺少域名或主机名"
        
        if require_https and parsed.scheme != 'https':
            return False, f"{field_name}必须使用HTTPS协议"
        
    except Exception:
        return False, f"{field_name}格式不正确"
    
    return True, None


def validate_phone(
    phone: Any,
    field_name: str = "手机号",
    allow_none: bool = False
) -> Tuple[bool, Optional[str]]:
    """验证手机号（中国大陆）
    
    Args:
        phone: 待验证的手机号
        field_name: 字段名称
        allow_none: 是否允许None值
        
    Returns:
        (是否有效, 错误消息)
    """
    if phone is None:
        if allow_none:
            return True, None
        return False, f"{field_name}不能为空"
    
    if not isinstance(phone, str):
        return False, f"{field_name}必须是字符串类型"
    
    if PHONE_REGEX.match(phone):
        return True, None
    else:
        return False, f"{field_name}格式不正确"


def validate_date(
    date_str: Any,
    field_name: str = "日期",
    format: str = "%Y-%m-%d",
    allow_none: bool = False
) -> Tuple[bool, Optional[str]]:
    """验证日期字符串
    
    Args:
        date_str: 待验证的日期字符串
        field_name: 字段名称
        format: 日期格式，默认YYYY-MM-DD
        allow_none: 是否允许None值
        
    Returns:
        (是否有效, 错误消息)
    """
    if date_str is None:
        if allow_none:
            return True, None
        return False, f"{field_name}不能为空"
    
    if not isinstance(date_str, str):
        return False, f"{field_name}必须是字符串类型"
    
    try:
        datetime.strptime(date_str, format)
        return True, None
    except ValueError:
        return False, f"{field_name}格式不正确，应为{format}"


def validate_datetime(
    datetime_str: Any,
    field_name: str = "日期时间",
    format: str = "%Y-%m-%d %H:%M:%S",
    allow_none: bool = False
) -> Tuple[bool, Optional[str]]:
    """验证日期时间字符串
    
    Args:
        datetime_str: 待验证的日期时间字符串
        field_name: 字段名称
        format: 日期时间格式
        allow_none: 是否允许None值
        
    Returns:
        (是否有效, 错误消息)
    """
    if datetime_str is None:
        if allow_none:
            return True, None
        return False, f"{field_name}不能为空"
    
    if not isinstance(datetime_str, str):
        return False, f"{field_name}必须是字符串类型"
    
    try:
        datetime.strptime(datetime_str, format)
        return True, None
    except ValueError:
        return False, f"{field_name}格式不正确，应为{format}"


def validate_choice(
    value: Any,
    choices: List[Any],
    field_name: str = "字段",
    allow_none: bool = False
) -> Tuple[bool, Optional[str]]:
    """验证值是否在可选范围内
    
    Args:
        value: 待验证的值
        choices: 可选值列表
        field_name: 字段名称
        allow_none: 是否允许None值
        
    Returns:
        (是否有效, 错误消息)
    """
    if value is None:
        if allow_none:
            return True, None
        return False, f"{field_name}不能为空"
    
    if value not in choices:
        choices_str = ", ".join(str(c) for c in choices)
        return False, f"{field_name}必须是以下值之一: {choices_str}"
    
    return True, None


def validate_json(
    json_str: Any,
    field_name: str = "JSON",
    allow_none: bool = False
) -> Tuple[bool, Optional[str]]:
    """验证JSON字符串
    
    Args:
        json_str: 待验证的JSON字符串
        field_name: 字段名称
        allow_none: 是否允许None值
        
    Returns:
        (是否有效, 错误消息)
    """
    if json_str is None:
        if allow_none:
            return True, None
        return False, f"{field_name}不能为空"
    
    if not isinstance(json_str, str):
        return False, f"{field_name}必须是字符串类型"
    
    try:
        json.loads(json_str)
        return True, None
    except json.JSONDecodeError:
        return False, f"{field_name}不是有效的JSON格式"


def validate_list(
    value: Any,
    field_name: str = "字段",
    min_length: int = 0,
    max_length: Optional[int] = None,
    allow_empty: bool = True,
    allow_none: bool = False
) -> Tuple[bool, Optional[str]]:
    """验证列表
    
    Args:
        value: 待验证的值
        field_name: 字段名称
        min_length: 最小长度
        max_length: 最大长度
        allow_empty: 是否允许空列表
        allow_none: 是否允许None值
        
    Returns:
        (是否有效, 错误消息)
    """
    if value is None:
        if allow_none:
            return True, None
        return False, f"{field_name}不能为空"
    
    if not isinstance(value, list):
        return False, f"{field_name}必须是列表类型"
    
    if not allow_empty and len(value) == 0:
        return False, f"{field_name}不能为空列表"
    
    if len(value) < min_length:
        return False, f"{field_name}长度不能小于{min_length}"
    
    if max_length is not None and len(value) > max_length:
        return False, f"{field_name}长度不能超过{max_length}"
    
    return True, None


def validate_dict(
    value: Any,
    field_name: str = "字段",
    required_keys: Optional[List[str]] = None,
    allow_empty: bool = True,
    allow_none: bool = False
) -> Tuple[bool, Optional[str]]:
    """验证字典
    
    Args:
        value: 待验证的值
        field_name: 字段名称
        required_keys: 必须包含的键
        allow_empty: 是否允许空字典
        allow_none: 是否允许None值
        
    Returns:
        (是否有效, 错误消息)
    """
    if value is None:
        if allow_none:
            return True, None
        return False, f"{field_name}不能为空"
    
    if not isinstance(value, dict):
        return False, f"{field_name}必须是字典类型"
    
    if not allow_empty and len(value) == 0:
        return False, f"{field_name}不能为空字典"
    
    if required_keys:
        missing_keys = []
        for key in required_keys:
            if key not in value:
                missing_keys.append(key)
        
        if missing_keys:
            keys_str = ", ".join(missing_keys)
            return False, f"{field_name}缺少必需的键: {keys_str}"
    
    return True, None


def validate_username(
    username: Any,
    field_name: str = "用户名",
    allow_none: bool = False
) -> Tuple[bool, Optional[str]]:
    """验证用户名
    
    Args:
        username: 待验证的用户名
        field_name: 字段名称
        allow_none: 是否允许None值
        
    Returns:
        (是否有效, 错误消息)
    """
    if username is None:
        if allow_none:
            return True, None
        return False, f"{field_name}不能为空"
    
    if not isinstance(username, str):
        return False, f"{field_name}必须是字符串类型"
    
    if USERNAME_REGEX.match(username):
        return True, None
    else:
        return False, f"{field_name}必须是3-20位的字母、数字或下划线"


def validate_password(
    password: Any,
    field_name: str = "密码",
    allow_none: bool = False
) -> Tuple[bool, Optional[str]]:
    """验证密码
    
    Args:
        password: 待验证的密码
        field_name: 字段名称
        allow_none: 是否允许None值
        
    Returns:
        (是否有效, 错误消息)
    """
    if password is None:
        if allow_none:
            return True, None
        return False, f"{field_name}不能为空"
    
    if not isinstance(password, str):
        return False, f"{field_name}必须是字符串类型"
    
    if PASSWORD_REGEX.match(password):
        return True, None
    else:
        return False, f"{field_name}长度必须为6-50位"


def validate_file_extension(
    filename: Any,
    allowed_extensions: List[str],
    field_name: str = "文件",
    allow_none: bool = False
) -> Tuple[bool, Optional[str]]:
    """验证文件扩展名
    
    Args:
        filename: 文件名
        allowed_extensions: 允许的扩展名列表（如['.jpg', '.png']）
        field_name: 字段名称
        allow_none: 是否允许None值
        
    Returns:
        (是否有效, 错误消息)
    """
    if filename is None:
        if allow_none:
            return True, None
        return False, f"{field_name}不能为空"
    
    if not isinstance(filename, str):
        return False, f"{field_name}必须是字符串类型"
    
    if '.' not in filename:
        return False, f"{field_name}没有扩展名"
    
    ext = filename.rsplit('.', 1)[1].lower()
    allowed = [ext.lower().lstrip('.') for ext in allowed_extensions]
    
    if ext in allowed:
        return True, None
    else:
        allowed_str = ", ".join(allowed_extensions)
        return False, f"{field_name}只支持以下格式: {allowed_str}"


def batch_validate(
    validators: Dict[str, Tuple[callable, Dict[str, Any]]],
    data: Dict[str, Any]
) -> Dict[str, List[str]]:
    """批量验证多个字段
    
    Args:
        validators: 验证器字典，格式为 {
            'field_name': (validate_func, {'param1': value1, ...})
        }
        data: 待验证的数据字典
        
    Returns:
        错误字典，格式为 {字段名: [错误消息列表]}，如果全部验证通过则返回空字典
    """
    errors = {}
    
    for field_name, (validate_func, kwargs) in validators.items():
        value = data.get(field_name)
        
        # 如果字段不在data中，设置值为None
        if field_name not in data:
            value = None
        
        is_valid, error_msg = validate_func(value, **kwargs)
        
        if not is_valid:
            if field_name not in errors:
                errors[field_name] = []
            errors[field_name].append(error_msg)
    
    return errors


# 导出常用函数
__all__ = [
    'validate_string',
    'validate_integer',
    'validate_number',
    'validate_email',
    'validate_url',
    'validate_phone',
    'validate_date',
    'validate_datetime',
    'validate_choice',
    'validate_json',
    'validate_list',
    'validate_dict',
    'validate_username',
    'validate_password',
    'validate_file_extension',
    'batch_validate',
]