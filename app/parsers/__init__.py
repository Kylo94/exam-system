"""文档解析器模块"""

from .base import BaseParser
from .docx_parser import DocxParser
from .text_parser import TextParser
from .factory import ParserFactory

__all__ = [
    'BaseParser',
    'DocxParser',
    'TextParser',
    'ParserFactory',
]