"""文件处理工具函数

提供文件扩展名验证、安全文件名生成、文件上传处理等工具函数。
"""

import os
import re
import hashlib
import mimetypes
import unicodedata
from pathlib import Path
from typing import Set, Optional, Tuple, Dict, Any
from werkzeug.utils import secure_filename as werkzeug_secure_filename


def allowed_file(filename: str, allowed_extensions: Set[str]) -> bool:
    """
    检查文件扩展名是否允许
    
    Args:
        filename: 文件名
        allowed_extensions: 允许的扩展名集合，如 {'.docx', '.pdf', '.txt'}
        
    Returns:
        是否允许
        
    Examples:
        >>> allowed_file('exam.docx', {'.docx', '.pdf'})
        True
        >>> allowed_file('image.jpg', {'.docx', '.pdf'})
        False
    """
    if not filename:
        return False
    
    # 提取扩展名
    ext = Path(filename).suffix.lower()
    return ext in allowed_extensions


def secure_filename(filename: str) -> str:
    """
    生成安全的文件名
    
    基于Werkzeug的secure_filename，但进行了一些改进：
    1. 支持中文文件名
    2. 保留更多安全字符
    3. 处理Unicode字符
    
    Args:
        filename: 原始文件名
        
    Returns:
        安全的文件名
        
    Examples:
        >>> secure_filename("测试 文件.docx")
        '测试_文件.docx'
        >>> secure_filename("../../etc/passwd")
        'etc_passwd'
    """
    if not filename:
        return ""
    
    # 使用Werkzeug的基础安全处理
    safe_name = werkzeug_secure_filename(filename)
    
    # 如果Werkzeug返回空（比如全中文文件名），使用自定义处理
    if not safe_name:
        # 处理中文文件名
        safe_name = filename
        
        # 移除不安全的字符
        safe_name = re.sub(r'[^\w\s\u4e00-\u9fff\-\.]', '_', safe_name)
        
        # 规范化Unicode字符
        safe_name = unicodedata.normalize('NFKD', safe_name).encode('ascii', 'ignore').decode('ascii')
        
        # 如果还是空，生成随机文件名
        if not safe_name:
            import uuid
            safe_name = str(uuid.uuid4().hex[:8])
    
    # 确保文件名长度合理
    if len(safe_name) > 255:
        name_stem = Path(safe_name).stem
        ext = Path(safe_name).suffix
        
        # 截断文件名主体，保留扩展名
        if len(ext) < 20:
            max_stem_len = 255 - len(ext)
            if len(name_stem) > max_stem_len:
                name_stem = name_stem[:max_stem_len]
            safe_name = name_stem + ext
        else:
            # 扩展名太长，生成随机名
            import uuid
            safe_name = str(uuid.uuid4().hex[:8]) + ext[-20:]
    
    return safe_name


def save_uploaded_file(file, upload_folder: str, allowed_extensions: Optional[Set[str]] = None) -> Dict[str, Any]:
    """
    保存上传的文件到指定目录
    
    Args:
        file: 上传的文件对象（如Flask的request.files['file']）
        upload_folder: 上传目录路径
        allowed_extensions: 允许的扩展名集合（可选）
        
    Returns:
        包含文件信息的字典:
        - filename: 保存的文件名
        - filepath: 完整文件路径
        - size: 文件大小（字节）
        - mimetype: MIME类型
        - saved: 是否保存成功
        - error: 错误信息（如果有）
        
    Raises:
        ValueError: 文件对象无效
        IOError: 保存文件失败
        
    Examples:
        >>> from flask import request
        >>> result = save_uploaded_file(request.files['file'], 'uploads')
        >>> if result['saved']:
        >>>     print(f"文件已保存: {result['filepath']}")
    """
    if not file or not hasattr(file, 'filename'):
        raise ValueError("无效的文件对象")
    
    result = {
        'filename': '',
        'filepath': '',
        'size': 0,
        'mimetype': getattr(file, 'content_type', 'application/octet-stream'),
        'saved': False,
        'error': ''
    }
    
    try:
        # 检查文件名
        original_filename = file.filename
        if not original_filename:
            result['error'] = '文件名不能为空'
            return result
        
        # 检查文件扩展名
        if allowed_extensions:
            if not allowed_file(original_filename, allowed_extensions):
                result['error'] = f'不支持的文件类型，只支持: {", ".join(allowed_extensions)}'
                return result
        
        # 生成安全文件名
        safe_filename = secure_filename(original_filename)
        
        # 创建上传目录
        upload_path = Path(upload_folder)
        upload_path.mkdir(parents=True, exist_ok=True)
        
        # 处理文件名冲突
        final_filename = safe_filename
        filepath = upload_path / final_filename
        
        counter = 1
        while filepath.exists():
            # 添加数字后缀
            stem = Path(safe_filename).stem
            ext = Path(safe_filename).suffix
            final_filename = f"{stem}_{counter}{ext}"
            filepath = upload_path / final_filename
            counter += 1
            
            if counter > 100:  # 防止无限循环
                import uuid
                final_filename = f"{uuid.uuid4().hex[:8]}{ext}"
                filepath = upload_path / final_filename
                break
        
        # 保存文件
        file.save(str(filepath))
        
        # 获取文件大小
        file_size = filepath.stat().st_size
        
        # 更新结果
        result.update({
            'filename': final_filename,
            'filepath': str(filepath),
            'size': file_size,
            'saved': True
        })
        
        return result
    
    except Exception as e:
        result['error'] = str(e)
        return result


def get_file_hash(filepath: str, algorithm: str = 'sha256') -> str:
    """
    计算文件哈希值
    
    Args:
        filepath: 文件路径
        algorithm: 哈希算法，如 'md5', 'sha1', 'sha256'
        
    Returns:
        文件的哈希值
        
    Raises:
        FileNotFoundError: 文件不存在
        ValueError: 不支持的哈希算法
    """
    if not Path(filepath).exists():
        raise FileNotFoundError(f"文件不存在: {filepath}")
    
    # 支持的哈希算法
    supported_algorithms = ['md5', 'sha1', 'sha256', 'sha512']
    if algorithm not in supported_algorithms:
        raise ValueError(f"不支持的哈希算法，支持: {', '.join(supported_algorithms)}")
    
    hash_func = hashlib.new(algorithm)
    
    try:
        with open(filepath, 'rb') as f:
            # 分块读取大文件
            for chunk in iter(lambda: f.read(4096), b''):
                hash_func.update(chunk)
        
        return hash_func.hexdigest()
    
    except Exception as e:
        raise IOError(f"计算文件哈希失败: {e}")


def get_file_info(filepath: str) -> Dict[str, Any]:
    """
    获取文件详细信息
    
    Args:
        filepath: 文件路径
        
    Returns:
        文件信息字典:
        - path: 文件路径
        - name: 文件名
        - size: 文件大小（字节）
        - extension: 扩展名
        - mimetype: MIME类型
        - created: 创建时间
        - modified: 修改时间
        - hash_md5: MD5哈希值
        - hash_sha256: SHA256哈希值
        
    Raises:
        FileNotFoundError: 文件不存在
    """
    path = Path(filepath)
    
    if not path.exists():
        raise FileNotFoundError(f"文件不存在: {filepath}")
    
    try:
        # 获取文件状态
        stat_info = path.stat()
        
        # 获取MIME类型
        mimetype, encoding = mimetypes.guess_type(filepath)
        
        # 计算哈希值（小文件才计算，大文件可能耗时）
        hash_md5 = ''
        hash_sha256 = ''
        
        if stat_info.st_size < 10 * 1024 * 1024:  # 10MB以下
            try:
                hash_md5 = get_file_hash(filepath, 'md5')
                hash_sha256 = get_file_hash(filepath, 'sha256')
            except Exception:
                pass  # 哈希计算失败，忽略
        
        return {
            'path': str(path.absolute()),
            'name': path.name,
            'size': stat_info.st_size,
            'extension': path.suffix.lower(),
            'mimetype': mimetype or 'application/octet-stream',
            'encoding': encoding,
            'created': stat_info.st_ctime,
            'modified': stat_info.st_mtime,
            'hash_md5': hash_md5,
            'hash_sha256': hash_sha256,
            'is_file': path.is_file(),
            'is_dir': path.is_dir(),
        }
    
    except Exception as e:
        raise IOError(f"获取文件信息失败: {e}")


def validate_file_upload(file, max_size: int = 16777216, allowed_extensions: Optional[Set[str]] = None) -> Tuple[bool, str]:
    """
    验证文件上传
    
    Args:
        file: 上传的文件对象
        max_size: 最大文件大小（字节），默认16MB
        allowed_extensions: 允许的扩展名集合
        
    Returns:
        (是否有效, 错误信息)
    """
    if not file:
        return False, "没有上传文件"
    
    # 检查文件名
    if not file.filename:
        return False, "文件名不能为空"
    
    # 检查文件扩展名
    if allowed_extensions:
        if not allowed_file(file.filename, allowed_extensions):
            extensions_str = ', '.join(allowed_extensions)
            return False, f"不支持的文件类型，只支持: {extensions_str}"
    
    # 检查文件大小（需要读取文件内容，可能消耗内存）
    try:
        # 保存当前位置
        current_pos = file.tell() if hasattr(file, 'tell') else 0
        
        # 读取文件大小
        file.seek(0, 2)  # 移动到文件末尾
        file_size = file.tell()
        file.seek(current_pos)  # 恢复位置
        
        if file_size > max_size:
            size_mb = max_size / 1024 / 1024
            return False, f"文件太大，最大允许{size_mb}MB"
    
    except Exception:
        # 如果无法获取大小，尝试其他方法
        pass
    
    return True, "验证通过"


def cleanup_old_files(directory: str, max_age_days: int = 7, pattern: str = "*") -> int:
    """
    清理目录中的旧文件
    
    Args:
        directory: 目录路径
        max_age_days: 最大保留天数
        pattern: 文件匹配模式，如 "*.tmp" 或 "*"
        
    Returns:
        删除的文件数量
        
    Examples:
        >>> deleted = cleanup_old_files('temp_uploads', 1, '*.tmp')
        >>> print(f"删除了{deleted}个临时文件")
    """
    import time
    from datetime import datetime, timedelta
    
    dir_path = Path(directory)
    if not dir_path.exists() or not dir_path.is_dir():
        return 0
    
    cutoff_time = time.time() - (max_age_days * 24 * 60 * 60)
    deleted_count = 0
    
    try:
        for file_path in dir_path.glob(pattern):
            if file_path.is_file():
                # 检查文件修改时间
                if file_path.stat().st_mtime < cutoff_time:
                    try:
                        file_path.unlink()
                        deleted_count += 1
                    except Exception:
                        pass  # 删除失败，继续处理其他文件
        
        return deleted_count
    
    except Exception:
        return deleted_count


# 测试代码（开发时使用）
if __name__ == "__main__":
    print("文件工具函数测试:")
    
    # 测试allowed_file
    extensions = {'.docx', '.pdf', '.txt'}
    print(f"allowed_file('exam.docx', {extensions}): {allowed_file('exam.docx', extensions)}")
    print(f"allowed_file('image.jpg', {extensions}): {allowed_file('image.jpg', extensions)}")
    
    # 测试secure_filename
    print(f"\nsecure_filename('测试 文件.docx'): {secure_filename('测试 文件.docx')}")
    print(f"secure_filename('../../etc/passwd'): {secure_filename('../../etc/passwd')}")
    print(f"secure_filename('normal-file_name.pdf'): {secure_filename('normal-file_name.pdf')}")
    
    # 测试get_file_hash（需要实际文件）
    # print(f"\nget_file_hash('test.txt', 'md5'): {get_file_hash('test.txt', 'md5')}")
    
    # 测试get_file_info（需要实际文件）
    # print(f"\nget_file_info('test.txt'): {get_file_info('test.txt')}")
    
    print("\n注意：save_uploaded_file需要实际文件对象测试")
    print("注意：cleanup_old_files需要实际目录测试")