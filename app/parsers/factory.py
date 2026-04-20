"""解析器工厂

根据文件格式自动选择相应的解析器。
"""

from typing import Dict, Optional, Type, Any
from pathlib import Path

from .base import BaseParser
from .question_parser import QuestionParser


class ParserFactory:
    """解析器工厂类"""

    # 注册的解析器映射 {文件扩展名: 解析器类}
    _parsers: Dict[str, Type[BaseParser]] = {
        '.docx': QuestionParser,
        '.doc': QuestionParser,
        '.txt': QuestionParser,
        '.text': QuestionParser,
    }

    @classmethod
    def get_parser(cls, file_path: str) -> Optional[BaseParser]:
        """根据文件路径获取相应的解析器实例

        Args:
            file_path: 文件路径

        Returns:
            解析器实例或None（如果不支持该格式）
        """
        path = Path(file_path)
        suffix = path.suffix.lower()

        parser_class = cls._parsers.get(suffix)
        if parser_class:
            return parser_class()

        return None

    @classmethod
    def can_parse(cls, file_path: str) -> bool:
        """检查是否可以解析该文件

        Args:
            file_path: 文件路径

        Returns:
            是否可以解析
        """
        path = Path(file_path)
        suffix = path.suffix.lower()
        return suffix in cls._parsers

    @classmethod
    def get_supported_formats(cls) -> Dict[str, str]:
        """获取支持的文件格式

        Returns:
            格式描述字典 {扩展名: 描述}
        """
        return {
            '.docx': 'Microsoft Word文档',
            '.doc': 'Microsoft Word文档（旧格式）',
            '.txt': '纯文本文件',
            '.text': '纯文本文件',
        }

    @classmethod
    def register_parser(cls, extension: str, parser_class: Type[BaseParser]) -> None:
        """注册新的解析器

        Args:
            extension: 文件扩展名（包括点，如 '.pdf'）
            parser_class: 解析器类
        """
        if not issubclass(parser_class, BaseParser):
            raise TypeError(f"解析器类必须继承自 BaseParser")

        cls._parsers[extension.lower()] = parser_class

    @classmethod
    def unregister_parser(cls, extension: str) -> None:
        """取消注册解析器

        Args:
            extension: 文件扩展名
        """
        cls._parsers.pop(extension.lower(), None)

    @classmethod
    def parse_file(cls, file_path: str, ai_config=None) -> Dict[str, Any]:
        """解析文件（自动选择解析器）

        Args:
            file_path: 文件路径
            ai_config: AI 配置对象（可选）

        Returns:
            解析后的数据

        Raises:
            FileNotFoundError: 文件不存在
            ValueError: 不支持的文件格式或解析失败
        """
        if not Path(file_path).exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")

        parser = QuestionParser(ai_config=ai_config)
        return parser.parse_document(file_path)

    @classmethod
    def parse_to_exam(cls, file_path: str, exam_title: str,
                     subject_id: int, level_id: int) -> Dict[str, Any]:
        """解析文件并转换为考试数据

        Args:
            file_path: 文件路径
            exam_title: 考试标题
            subject_id: 科目ID
            level_id: 难度级别ID

        Returns:
            考试数据字典

        Raises:
            ValueError: 不支持的文件格式或解析失败
        """
        result = cls.parse_file(file_path)
        questions = result.get('questions', [])

        return {
            'title': exam_title,
            'subject_id': subject_id,
            'level_id': level_id,
            'description': f"从文档 '{Path(file_path).name}' 导入",
            'duration_minutes': len(questions) * 2,
            'questions': questions,
            'question_count': len(questions)
        }