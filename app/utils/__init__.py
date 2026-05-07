"""工具函数模块"""

from .image_utils import (
    extract_base64_from_docx,
    get_image_type,
    resize_image,
    save_image_to_file,
    validate_image_file,
    validate_image_size,
)
from .question_utils import (
    detect_question_type,
    format_options,
    normalize_answer,
    validate_question_data,
)
from .validators import (
    batch_validate,
    validate_choice,
    validate_date,
    validate_datetime,
    validate_dict,
    validate_email,
    validate_file_extension,
    validate_integer,
    validate_json,
    validate_list,
    validate_number,
    validate_password,
    validate_phone,
    validate_string,
    validate_url,
    validate_username,
)

__all__ = [
    # 题目工具
    'detect_question_type',
    'normalize_answer',
    'format_options',
    'validate_question_data',

    # 图片工具
    'get_image_type',
    'validate_image_size',
    'extract_base64_from_docx',
    'save_image_to_file',
    'resize_image',
    'validate_image_file',

    # 数据验证工具
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
