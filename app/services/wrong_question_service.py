"""
错题记录服务
"""
from typing import List, Optional

from app.models.question import Question
from app.models.submission import Submission
from app.models.wrong_question import WrongQuestion


class WrongQuestionService:
    """错题记录服务"""

    @staticmethod
    async def record_wrong_question(
        student_id: int,
        question_id: int,
        submission_id: int,
        student_answer: str,
        correct_answer: str
    ) -> WrongQuestion:
        """记录一道错题（如果已存在则不重复记录）"""
        # 检查是否已经记录过这道错题
        existing = await WrongQuestion.filter(
            student_id=student_id,
            question_id=question_id
        ).first()

        if existing:
            # 更新答题记录
            existing.submission_id = submission_id
            existing.student_answer = student_answer
            existing.correct_answer = correct_answer
            existing.is_wrong = True
            await existing.save()
            return existing

        return await WrongQuestion.create(
            student_id=student_id,
            question_id=question_id,
            submission_id=submission_id,
            student_answer=student_answer,
            correct_answer=correct_answer,
            is_wrong=True
        )

    @staticmethod
    async def record_from_submission(submission: Submission, answers: List[dict]) -> int:
        """从答题记录中批量记录错题

        Args:
            submission: 答题提交记录
            answers: 答题答案列表 [{"question_id": xxx, "student_answer": "xxx", "is_correct": False}, ...]

        Returns:
            记录的错题数量
        """
        wrong_count = 0
        for answer in answers:
            if not answer.get("is_correct", True):
                # 获取题目正确答案
                question = await Question.get_or_none(id=answer["question_id"])
                if question:
                    await WrongQuestionService.record_wrong_question(
                        student_id=submission.user_id,
                        question_id=answer["question_id"],
                        submission_id=submission.id,
                        student_answer=answer.get("student_answer", ""),
                        correct_answer=question.correct_answer
                    )
                    wrong_count += 1

        return wrong_count

    @staticmethod
    async def get_student_wrong_questions(
        student_id: int,
        subject_id: Optional[int] = None,
        knowledge_point_id: Optional[int] = None,
        limit: int = 50
    ) -> List[WrongQuestion]:
        """获取学生的错题列表

        Args:
            student_id: 学生ID
            subject_id: 科目ID（可选）
            knowledge_point_id: 知识点ID（可选）
            limit: 返回数量限制

        Returns:
            错题列表
        """
        query = WrongQuestion.filter(student_id=student_id).prefetch_related(
            "question", "submission"
        ).order_by("-created_at")

        wrong_questions = await query.limit(limit * 2).all()  # 多取一些，后面再过滤

        result = []
        for wq in wrong_questions:
            if wq.question:
                if subject_id and wq.question.exam and wq.question.exam.subject_id != subject_id:
                    continue
                if knowledge_point_id and wq.question.knowledge_point_id != knowledge_point_id:
                    continue
                result.append(wq)
                if len(result) >= limit:
                    break

        return result

    @staticmethod
    async def get_wrong_questions_by_kp(student_id: int, knowledge_point_id: int) -> List[WrongQuestion]:
        """获取学生某个知识点的错题（支持tags匹配）"""
        kp = await KnowledgePoint.get_or_none(id=knowledge_point_id)
        if not kp:
            return []

        if kp.tags:
            # tags匹配
            all_wrong = await WrongQuestion.filter(student_id=student_id).prefetch_related("question").all()
            kp_tags = set(t.strip().lower() for t in kp.tags if t.strip())
            return [wq for wq in all_wrong if wq.question and any(t in kp_tags for t in (wq.question.tags or []))]
        else:
            # 降级：按knowledge_point_id匹配
            return await WrongQuestion.filter(
                student_id=student_id,
                question__knowledge_point_id=knowledge_point_id
            ).prefetch_related("question").all()

    @staticmethod
    async def get_wrong_count_by_subject(student_id: int) -> dict:
        """按科目统计学生的错题数量"""
        wrong_questions = await WrongQuestion.filter(student_id=student_id).prefetch_related(
            "question", "question__exam"
        ).all()

        count_by_subject = {}
        for wq in wrong_questions:
            if wq.question and wq.question.exam:
                subject_id = wq.question.exam.subject_id
                if subject_id not in count_by_subject:
                    count_by_subject[subject_id] = 0
                count_by_subject[subject_id] += 1

        return count_by_subject

    @staticmethod
    async def delete_wrong_question(wrong_id: int, student_id: int) -> bool:
        """删除一条错题记录"""
        wq = await WrongQuestion.get_or_none(id=wrong_id, student_id=student_id)
        if wq:
            await wq.delete()
            return True
        return False

    @staticmethod
    async def clear_wrong_questions(student_id: int, subject_id: Optional[int] = None) -> int:
        """清空学生的错题记录"""
        query = WrongQuestion.filter(student_id=student_id)
        if subject_id:
            query = query.filter(question__exam__subject_id=subject_id)

        wqs = await query.all()
        count = len(wqs)
        for wq in wqs:
            await wq.delete()
        return count

    @staticmethod
    async def get_practice_questions(
        student_id: int,
        subject_id: int,
        limit: int = 10
    ) -> List[Question]:
        """获取学生需要练习的错题对应的题目"""
        # 获取该科目下的错题
        wrong_questions = await WrongQuestion.filter(
            student_id=student_id,
            question__exam__subject_id=subject_id
        ).prefetch_related("question").all()

        # 获取题目ID列表（去重）
        question_ids = list(set(wq.question_id for wq in wrong_questions if wq.question))

        if not question_ids:
            return []

        # 获取题目（预加载关联数据）
        questions = await Question.filter(id__in=question_ids).limit(limit).prefetch_related('exam__subject').all()
        return questions
