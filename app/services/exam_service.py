"""试卷服务"""
import logging
from typing import Any, Dict, List

from app.models.exam import Exam
from app.models.question import Question
from app.models.user import User
from app.services.exceptions import NotFoundException, ValidationException

logger = logging.getLogger(__name__)


class ExamService:
    """试卷业务逻辑"""

    @staticmethod
    async def get_exam_or_404(exam_id: int) -> Exam:
        """获取试卷，不存在则抛异常"""
        exam = await Exam.get_or_none(id=exam_id)
        if not exam:
            raise NotFoundException("试卷", exam_id)
        return exam

    @staticmethod
    async def create_exam(
        title: str,
        subject_id: int,
        creator: User,
        level_id: int = None,
        duration_minutes: int = 60,
        total_points: int = 100,
        pass_score: int = 60,
        is_published: bool = False,
    ) -> Exam:
        """创建试卷"""
        if not title:
            raise ValidationException("试卷标题不能为空")

        return await Exam.create(
            title=title,
            subject_id=subject_id,
            level_id=level_id,
            creator=creator,
            duration_minutes=duration_minutes,
            total_points=total_points,
            pass_score=pass_score,
            is_published=is_published,
        )

    @staticmethod
    async def update_exam(
        exam_id: int,
        title: str = None,
        subject_id: int = None,
        level_id: int = None,
        duration_minutes: int = None,
        total_points: int = None,
        pass_score: int = None,
        is_published: bool = None,
    ) -> Exam:
        """更新试卷"""
        exam = await ExamService.get_exam_or_404(exam_id)

        if title is not None:
            exam.title = title
        if subject_id is not None:
            exam.subject_id = subject_id
        if level_id is not None:
            exam.level_id = level_id
        if duration_minutes is not None:
            exam.duration_minutes = duration_minutes
        if total_points is not None:
            exam.total_points = total_points
        if pass_score is not None:
            exam.pass_score = pass_score
        if is_published is not None:
            exam.is_published = is_published

        await exam.save()
        return exam

    @staticmethod
    async def delete_exam(exam_id: int) -> None:
        """删除试卷"""
        exam = await ExamService.get_exam_or_404(exam_id)
        await exam.delete()

    @staticmethod
    async def batch_delete(exam_ids: List[int]) -> int:
        """批量删除试卷"""
        await Exam.filter(id__in=exam_ids).delete()
        return len(exam_ids)

    @staticmethod
    async def batch_publish(exam_ids: List[int], is_published: bool = True) -> int:
        """批量发布/取消发布"""
        await Exam.filter(id__in=exam_ids).update(is_published=is_published)
        return len(exam_ids)

    @staticmethod
    async def create_questions_from_data(
        exam: Exam,
        questions_data: List[Dict[str, Any]]
    ) -> tuple[int, int]:
        """从数据创建题目（只保存tags，不关联知识点）

        Args:
            exam: 试卷实例
            questions_data: 题目数据列表

        Returns:
            (成功数, 失败数)
        """
        created = 0
        failed = 0

        for idx, q_data in enumerate(questions_data):
            try:
                images = q_data.get('images', [])
                if not isinstance(images, list):
                    images = [images] if images else []

                # 处理选项格式
                options = q_data.get('options', {})
                if isinstance(options, list):
                    # 提取选项中的图片信息，保存到 question_metadata
                    options_images = {}
                    for opt in options:
                        opt_id = opt.get('id', '')
                        if opt.get('has_image') and opt.get('image_path'):
                            options_images[opt_id] = {
                                'has_image': True,
                                'image_path': opt.get('image_path')
                            }
                    options = {opt.get('id', chr(65+i)): opt.get('text', '') for i, opt in enumerate(options)}
                    if options_images:
                        question_metadata = q_data.get('question_metadata', {})
                        if 'options_images' not in question_metadata:
                            question_metadata['options_images'] = {}
                        question_metadata['options_images'].update(options_images)
                        q_data['question_metadata'] = question_metadata

                # 获取标签
                tags = q_data.get('tags', [])

                q_type = q_data.get('type', 'choice') or 'choice'
                logger.debug(f"创建题目 idx={idx}: type={q_type}, "
                           f"options_type={type(options).__name__}, "
                           f"options_len={len(options) if options else 0}, "
                           f"options_sample={str(options)[:200] if options else 'EMPTY'}")

                await Question.create(
                    exam=exam,
                    type=q_type,
                    content=q_data.get('content') or '题目内容',
                    options=options,
                    correct_answer=q_data.get('correct_answer') or '',
                    points=q_data.get('points') or 10,
                    difficulty=q_data.get('difficulty') or 1,
                    explanation=q_data.get('explanation'),
                    images=images,
                    question_metadata=q_data.get('question_metadata', {}),
                    order_num=q_data.get('index', idx + 1) or (idx + 1),
                    tags=tags,
                )

                created += 1
            except Exception:
                logger.exception(f"创建题目失败 idx={idx}")
                failed += 1

        return created, failed
