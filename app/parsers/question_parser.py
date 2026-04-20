"""题目解析统一入口"""

from typing import Dict, List, Any, Optional
from pathlib import Path


class QuestionParser:
    """题目解析统一入口"""

    def __init__(self, ai_config=None, upload_folder: str = 'uploads/images'):
        """
        初始化题目解析器

        Args:
            ai_config: AI 配置对象
            upload_folder: 图片保存目录
        """
        self.ai_config = ai_config
        self.upload_folder = upload_folder
        self._log_messages = []

    def parse_document(self, file_path: str) -> Dict[str, Any]:
        """
        解析文档

        Args:
            file_path: 文档路径

        Returns:
            解析结果字典
        """
        self._log_messages = []
        self._add_log(f"开始解析文档: {Path(file_path).name}", 'info')

        # 1. 提取文本和图片
        self._add_log("步骤1: 从文档提取文本内容...", 'info')
        text, image_info = self._extract_content(file_path)
        self._add_log(f"文本提取完成，共 {len(text)} 个字符", 'success')
        self._add_log(f"检测到 {len(image_info)} 张图片", 'success')

        # 2. 使用 AI 或规则解析
        self._add_log("步骤2: 解析试题...", 'info')
        questions = self._parse_questions(text, image_info)
        self._add_log(f"解析完成，共识别 {len(questions)} 道试题", 'success')

        return {
            'success': True,
            'questions': questions,
            'question_count': len(questions),
            'raw_text': text,
            'parse_log': '\n'.join(self._log_messages)
        }

    def _extract_content(self, file_path: str):
        """提取文档内容"""
        from .docx_extractor import DocxExtractor

        suffix = Path(file_path).suffix.lower()
        if suffix == '.docx':
            extractor = DocxExtractor(upload_folder=self.upload_folder)
            return extractor.extract_text_and_images(file_path)
        else:
            # 其他格式使用纯文本提取
            extractor = DocxExtractor(upload_folder=self.upload_folder, extract_images=False)
            return extractor.extract_text(file_path), []

    def _parse_questions(self, text: str, image_info: List[Dict]) -> List[Dict[str, Any]]:
        """解析试题"""
        if self.ai_config:
            # 使用 AI 解析
            from .ai_parser import AIParser

            try:
                parser = AIParser(ai_config=self.ai_config)
                return parser.parse(text, image_info)
            except Exception as e:
                self._add_log(f"AI解析失败: {str(e)}", 'error')
                # 回退到规则解析
                return self._parse_with_rules(text, image_info)
        else:
            # 使用规则解析
            return self._parse_with_rules(text, image_info)

    def _parse_with_rules(self, text: str, image_info: List[Dict]) -> List[Dict[str, Any]]:
        """使用规则解析"""
        from .rule_parser import RuleParser

        parser = RuleParser()
        return parser.parse(text, image_info)

    def _add_log(self, message: str, level: str = 'info'):
        """添加日志"""
        from datetime import datetime
        timestamp = datetime.now().strftime('%H:%M:%S')
        icon = {'info': 'ℹ️', 'success': '✅', 'warning': '⚠️', 'error': '❌'}.get(level, '•')
        self._log_messages.append(f"[{timestamp}] {icon} {message}")

    def get_logs(self) -> str:
        """获取解析日志"""
        return '<br>'.join(self._log_messages)
