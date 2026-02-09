"""工具函数模块"""

from .error_handlers import (
    register_handlers,
    APIError,
    ValidationError,
    NotFoundError,
    AuthenticationError,
    AuthorizationError,
)

from .question_utils import (
    detect_question_type,
    normalize_answer,
    format_options,
    validate_question_data,
)

from .image_utils import (
    get_image_type,
    validate_image_size,
    extract_base64_from_docx,
    save_image_to_file,
    resize_image,
    validate_image_file,
)

from .file_utils import (
    allowed_file,
    secure_filename,
    save_uploaded_file,
    get_file_hash,
    get_file_info,
    validate_file_upload,
    cleanup_old_files,
)

from .response_utils import (
    success_response,
    error_response,
    pagination_response,
    validation_error_response,
    make_response,
    api_response,
)

from .validators import (
    validate_string,
    validate_integer,
    validate_number,
    validate_email,
    validate_url,
    validate_phone,
    validate_date,
    validate_datetime,
    validate_choice,
    validate_json,
    validate_list,
    validate_dict,
    validate_username,
    validate_password,
    validate_file_extension,
    batch_validate,
)

__all__ = [
    # 错误处理
    'register_handlers',
    'APIError',
    'ValidationError',
    'NotFoundError',
    'AuthenticationError',
    'AuthorizationError',
    
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
    
    # 文件工具
    'allowed_file',
    'secure_filename',
    'save_uploaded_file',
    'get_file_hash',
    'get_file_info',
    'validate_file_upload',
    'cleanup_old_files',
    
    # 响应工具
    'success_response',
    'error_response',
    'pagination_response',
    'validation_error_response',
    'make_response',
    'api_response',
    
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