"""图片处理工具函数

提供图片类型检测、大小验证、从Word文档提取图片等工具函数。
"""

import os
import re
import base64
import imghdr
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path


def get_image_type(filename: str) -> str:
    """
    根据文件扩展名返回图片类型
    
    Args:
        filename: 图片文件名或路径
        
    Returns:
        图片类型，如 'jpeg', 'png', 'gif', 'webp'，未知类型返回 'unknown'
        
    Examples:
        >>> get_image_type('image.jpg')
        'jpeg'
        >>> get_image_type('photo.png')
        'png'
    """
    if not filename:
        return 'unknown'
    
    # 扩展名到类型的映射
    ext_map = {
        '.jpg': 'jpeg', '.jpeg': 'jpeg', '.jpe': 'jpeg',
        '.png': 'png',
        '.gif': 'gif',
        '.bmp': 'bmp',
        '.webp': 'webp',
        '.svg': 'svg', '.svgz': 'svg',
        '.tiff': 'tiff', '.tif': 'tiff',
    }
    
    # 提取扩展名
    path = Path(filename)
    ext = path.suffix.lower()
    
    return ext_map.get(ext, 'unknown')


def validate_image_size(data: bytes, max_size: int = 5242880) -> bool:
    """
    验证图片大小
    
    Args:
        data: 图片二进制数据
        max_size: 最大允许大小（字节），默认5MB
        
    Returns:
        是否有效
        
    Examples:
        >>> with open('image.jpg', 'rb') as f:
        >>>     data = f.read()
        >>> validate_image_size(data, 10*1024*1024)  # 10MB限制
    """
    if not data:
        return False
    
    # 检查数据大小
    if len(data) > max_size:
        return False
    
    # 检查是否为有效图片
    try:
        image_type = imghdr.what(None, data)
        return image_type is not None
    except Exception:
        return False


def extract_base64_from_docx(file_path: str) -> List[Dict[str, Any]]:
    """
    从Word文档提取图片并转换为base64编码
    
    Args:
        file_path: Word文档路径
        
    Returns:
        图片列表，每个元素包含:
        - data: base64编码的图片数据
        - type: 图片类型
        - size: 图片大小（字节）
        - filename: 原始文件名（如果有）
        
    Raises:
        FileNotFoundError: 文件不存在
        ImportError: python-docx未安装
        ValueError: 文件格式不支持
        
    Examples:
        >>> images = extract_base64_from_docx('exam.docx')
        >>> for img in images:
        >>>     print(f"图片类型: {img['type']}, 大小: {img['size']}字节")
    """
    try:
        import docx
        from docx.image.exceptions import UnrecognizedImageError
    except ImportError:
        raise ImportError("请安装python-docx: pip install python-docx")
    
    # 验证文件
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"文件不存在: {file_path}")
    
    if path.suffix.lower() not in ['.docx', '.doc']:
        raise ValueError(f"不支持的文件格式: {path.suffix}")
    
    images = []
    
    try:
        # 打开文档
        doc = docx.Document(file_path)
        
        # 提取文档中的所有图片
        # 注意：python-docx的图片提取方式有限，这里使用文档关系方法
        if hasattr(doc, 'part') and hasattr(doc.part, 'related_parts'):
            # 提取所有图片关系
            for rel_id, rel in doc.part.related_parts.items():
                if hasattr(rel, 'blob'):
                    blob = rel.blob
                    if blob:
                        # 尝试检测图片类型
                        image_type = imghdr.what(None, blob)
                        if image_type:
                            # 转换为base64
                            base64_data = base64.b64encode(blob).decode('utf-8')
                            
                            images.append({
                                'data': base64_data,
                                'type': image_type,
                                'size': len(blob),
                                'filename': f"image_{len(images)+1}.{image_type}",
                                'rel_id': rel_id
                            })
        
        # 另一种方法：遍历所有段落提取内联图片
        for i, paragraph in enumerate(doc.paragraphs):
            for run in paragraph.runs:
                # 检查run中是否有图片
                if hasattr(run, '_element'):
                    element = run._element
                    # 查找图片元素
                    drawing_elements = element.xpath('.//a:blip')
                    for drawing in drawing_elements:
                        # 获取图片引用
                        embed = drawing.get('{http://schemas.openxmlformats.org/drawingml/2006/main}embed')
                        if embed:
                            # 从文档关系获取图片数据
                            try:
                                image_part = doc.part.related_parts.get(embed)
                                if image_part and hasattr(image_part, 'blob'):
                                    blob = image_part.blob
                                    if blob:
                                        image_type = imghdr.what(None, blob)
                                        if image_type:
                                            base64_data = base64.b64encode(blob).decode('utf-8')
                                            
                                            images.append({
                                                'data': base64_data,
                                                'type': image_type,
                                                'size': len(blob),
                                                'filename': f"para{i+1}_img{len(images)+1}.{image_type}",
                                                'paragraph_index': i,
                                                'run_index': paragraph.runs.index(run)
                                            })
                            except Exception:
                                pass
        
        return images
    
    except Exception as e:
        raise ValueError(f"提取图片失败: {e}")


def save_image_to_file(base64_data: str, output_path: str, filename: Optional[str] = None) -> str:
    """
    将base64图片数据保存到文件
    
    Args:
        base64_data: base64编码的图片数据
        output_path: 输出目录
        filename: 文件名（可选，不提供则自动生成）
        
    Returns:
        保存的文件路径
        
    Raises:
        ValueError: base64数据无效
        IOError: 保存文件失败
    """
    if not base64_data:
        raise ValueError("base64数据不能为空")
    
    # 解码base64
    try:
        image_data = base64.b64decode(base64_data)
    except Exception as e:
        raise ValueError(f"base64解码失败: {e}")
    
    # 检测图片类型
    image_type = imghdr.what(None, image_data)
    if not image_type:
        raise ValueError("无法识别图片类型")
    
    # 生成文件名
    if not filename:
        import uuid
        filename = f"{uuid.uuid4().hex[:8]}.{image_type}"
    
    # 确保扩展名匹配
    if not filename.lower().endswith(f'.{image_type}'):
        filename = f"{Path(filename).stem}.{image_type}"
    
    # 创建输出目录
    output_dir = Path(output_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 保存文件
    file_path = output_dir / filename
    try:
        with open(file_path, 'wb') as f:
            f.write(image_data)
        return str(file_path)
    except Exception as e:
        raise IOError(f"保存图片失败: {e}")


def resize_image(image_data: bytes, max_width: int = 800, max_height: int = 600) -> bytes:
    """
    调整图片大小（需要Pillow库）
    
    Args:
        image_data: 图片二进制数据
        max_width: 最大宽度
        max_height: 最大高度
        
    Returns:
        调整大小后的图片数据
        
    Raises:
        ImportError: Pillow未安装
    """
    try:
        from PIL import Image
        import io
    except ImportError:
        raise ImportError("请安装Pillow: pip install Pillow")
    
    try:
        # 打开图片
        image = Image.open(io.BytesIO(image_data))
        
        # 计算新尺寸
        original_width, original_height = image.size
        ratio = min(max_width / original_width, max_height / original_height)
        
        if ratio < 1:
            # 需要缩小
            new_width = int(original_width * ratio)
            new_height = int(original_height * ratio)
            image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        # 保存为JPEG格式（压缩）
        output = io.BytesIO()
        if image.mode in ('RGBA', 'LA'):
            # 透明背景转换为白色背景
            background = Image.new('RGB', image.size, (255, 255, 255))
            background.paste(image, mask=image.split()[-1])
            image = background
        
        image.save(output, format='JPEG', quality=85)
        return output.getvalue()
    
    except Exception as e:
        raise ValueError(f"调整图片大小失败: {e}")


def validate_image_file(file_path: str, max_size: int = 5242880) -> Tuple[bool, str]:
    """
    验证图片文件
    
    Args:
        file_path: 图片文件路径
        max_size: 最大文件大小（字节）
        
    Returns:
        (是否有效, 错误信息)
    """
    try:
        path = Path(file_path)
        
        # 检查文件是否存在
        if not path.exists():
            return False, "文件不存在"
        
        # 检查文件大小
        if path.stat().st_size > max_size:
            return False, f"文件大小超过限制（最大{max_size//1024//1024}MB）"
        
        # 检查文件类型
        with open(file_path, 'rb') as f:
            header = f.read(32)
        
        image_type = imghdr.what(None, header)
        if not image_type:
            return False, "不是有效的图片文件"
        
        return True, "验证通过"
    
    except Exception as e:
        return False, f"验证失败: {e}"


# 测试代码（开发时使用）
if __name__ == "__main__":
    # 测试get_image_type
    print("图片类型检测:")
    print(get_image_type("photo.jpg"))  # jpeg
    print(get_image_type("image.png"))  # png
    print(get_image_type("animation.gif"))  # gif
    
    # 测试validate_image_size（模拟数据）
    test_data = b'fake_image_data'
    print(f"\n图片大小验证: {validate_image_size(test_data, 100)}")  # True
    
    # 测试validate_image_file
    # 注意：需要实际图片文件进行测试
    # print(validate_image_file('test.jpg', 1024*1024))
    
    print("\n注意：extract_base64_from_docx需要实际Word文档进行测试")
    print("注意：save_image_to_file和resize_image需要实际数据测试")