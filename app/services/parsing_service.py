"""文档解析服务"""
import logging
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from app.parsers.ai_parser import AIParser
from app.parsers.docx_extractor import DocxExtractor
from app.parsers.rule_parser import RuleParser

logger = logging.getLogger(__name__)


class ParsingService:
    """统一的文档解析服务"""

    @staticmethod
    async def parse_document(
        file_path: str,
        filename: str,
        parse_method: str = "rule",
        ai_config=None,
        image_info: List[Dict] = None,
        existing_kps: List[str] = None
    ) -> Tuple[str, List[Dict[str, Any]], List[Dict]]:
        """解析文档并返回题目列表

        Args:
            file_path: 文件路径
            filename: 文件名
            parse_method: 解析方式 "rule" 或 "ai"
            ai_config: AI配置对象
            image_info: 图片信息列表
            existing_kps: 已有的知识点名称列表

        Returns:
            (raw_text, questions_data, image_info)
        """
        # 1. 提取文本和图片
        extractor = DocxExtractor(upload_folder='uploads/images')
        raw_text, extracted_images = extractor.extract_text_and_images(file_path)

        if not raw_text:
            return "", [], extracted_images or []

        # 2. 规则拆分题目
        rule_parser = RuleParser()
        questions = rule_parser.parse(raw_text, extracted_images)

        if not questions:
            return raw_text, [], extracted_images or []

        # 3. AI增强（如需要）
        if parse_method == "ai" and ai_config:
            try:
                ai_parser = AIParser(ai_config=ai_config)
                questions = ai_parser.batch_enhance_questions(questions, extracted_images, existing_kps)
            except Exception as e:
                logger.warning(f"AI增强失败，使用本地解析结果: {e}")

        return raw_text, questions, extracted_images or []

    @staticmethod
    async def parse_file_stream(
        file_content: bytes,
        filename: str,
        parse_method: str = "rule",
        ai_config=None
    ) -> Tuple[str, List[Dict[str, Any]], List[Dict]]:
        """从文件内容流解析文档

        Args:
            file_content: 文件内容字节
            filename: 文件名
            parse_method: 解析方式
            ai_config: AI配置对象

        Returns:
            (raw_text, questions_data, image_info)
        """
        suffix = Path(filename).suffix.lower()
        tmp_path = None

        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                tmp.write(file_content)
                tmp_path = tmp.name

            return await ParsingService.parse_document(
                tmp_path, filename, parse_method, ai_config
            )
        finally:
            if tmp_path and Path(tmp_path).exists():
                Path(tmp_path).unlink()

    @staticmethod
    def build_preview_data(
        title: str,
        subject_id: int,
        level_id: int,
        questions: List[Dict[str, Any]],
        existing_kps: List[Any] = None
    ) -> Dict[str, Any]:
        """构建预览数据结构

        Args:
            title: 试卷标题
            subject_id: 科目ID
            level_id: 等级ID
            questions: 题目列表
            existing_kps: 已有的知识点列表

        Returns:
            预览数据结构
        """
        kp_suggestions = []
        if existing_kps:
            kp_suggestions = [kp.name for kp in existing_kps[:20]]

        preview_questions = []
        for idx, q in enumerate(questions):
            preview_questions.append({
                "index": idx + 1,
                "type": q.get('type', 'unknown'),
                "content": q.get('content', ''),
                "options": q.get('options', []),
                "correct_answer": q.get('correct_answer', ''),
                "points": q.get('points', 10),
                "difficulty": q.get('difficulty', 1),
                "explanation": q.get('explanation', ''),
                "knowledge_point_names": q.get('knowledge_point_names', []),
                "images": q.get('images', []),
                "question_metadata": q.get('question_metadata', {}),
            })

        return {
            "exam_title": title,
            "subject_id": subject_id,
            "level_id": level_id,
            "total_questions": len(questions),
            "suggested_knowledge_points": kp_suggestions,
            "questions": preview_questions
        }