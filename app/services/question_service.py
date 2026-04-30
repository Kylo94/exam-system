"""题目服务"""
import json
from typing import List, Dict, Any, Optional
from app.models.question import Question
from app.models.exam import Exam
from app.models.knowledge_point import KnowledgePoint
from app.services.exceptions import NotFoundException, ValidationException


class QuestionService:
    """题目业务逻辑"""

    @staticmethod
    async def get_question_or_404(question_id: int) -> Question:
        """获取题目，不存在则抛异常"""
        question = await Question.get_or_none(id=question_id)
        if not question:
            raise NotFoundException("题目", question_id)
        return question

    @staticmethod
    async def get_questions_by_exam(exam_id: int) -> List[Question]:
        """获取试卷下的所有题目"""
        return await Question.filter(exam_id=exam_id).prefetch_related(
            "knowledge_point"
        ).order_by("order_num")

    @staticmethod
    async def create_question(
        exam_id: int,
        type: str = 'single_choice',
        content: str = '',
        correct_answer: str = '',
        points: int = 10,
        options: Dict = None,
        explanation: str = None,
        difficulty: int = 1,
        has_image: bool = False,
        image_data: str = None,
        question_metadata: Dict = None,
    ) -> Question:
        """创建题目"""
        exam = await Exam.get_or_none(id=exam_id)
        if not exam:
            raise NotFoundException("试卷", exam_id)

        order_num = await Question.filter(exam_id=exam_id).count() + 1

        return await Question.create(
            exam=exam,
            type=type,
            content=content,
            correct_answer=correct_answer,
            points=points,
            options=options or {},
            explanation=explanation,
            difficulty=difficulty,
            has_image=has_image,
            image_data=image_data,
            question_metadata=question_metadata or {},
            order_num=order_num,
        )

    @staticmethod
    async def update_question(
        question_id: int,
        type: str = None,
        content: str = None,
        correct_answer: str = None,
        points: int = None,
        options: Any = None,
        explanation: str = None,
        difficulty: int = None,
        image_data: str = None,
        question_metadata: Any = None,
        knowledge_point_id: int = None,
    ) -> Question:
        """更新题目"""
        question = await QuestionService.get_question_or_404(question_id)

        if type:
            question.type = type
        if content:
            question.content = content
        if correct_answer:
            question.correct_answer = correct_answer
        if points:
            question.points = points
        if options:
            if isinstance(options, str):
                options = json.loads(options)
            question.options = options
        if explanation is not None:
            question.explanation = explanation
        if difficulty:
            question.difficulty = difficulty

        # 处理知识点分配
        if knowledge_point_id is not None:
            if knowledge_point_id == 0:
                question.knowledge_point = None
            else:
                question.knowledge_point_id = knowledge_point_id

        # 处理图片
        if image_data is not None:
            if image_data == '':
                question.images = []
            else:
                question.images = [image_data]

        if question_metadata is not None:
            if isinstance(question_metadata, str):
                question_metadata = json.loads(question_metadata)
            question.question_metadata = question_metadata or {}

        await question.save()
        return question

    @staticmethod
    async def delete_question(question_id: int) -> None:
        """删除题目"""
        question = await QuestionService.get_question_or_404(question_id)
        await question.delete()

    @staticmethod
    async def batch_delete(question_ids: List[int]) -> int:
        """批量删除题目"""
        await Question.filter(id__in=question_ids).delete()
        return len(question_ids)