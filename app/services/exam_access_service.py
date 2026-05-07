"""
学生试卷授权服务
"""
from typing import List, Optional

from app.models.exam import Exam
from app.models.student_exam_access import StudentExamAccess


class ExamAccessService:
    """学生试卷授权服务"""

    @staticmethod
    async def grant_access(
        student_id: int,
        teacher_id: int,
        subject_id: int,
        level_id: Optional[int] = None,
        granted_by_id: int = None
    ) -> StudentExamAccess:
        """授权学生访问某科目/等级的试卷"""
        # 检查是否已存在相同授权
        query = StudentExamAccess.filter(
            student_id=student_id,
            subject_id=subject_id
        )
        if level_id:
            query = query.filter(level_id=level_id)
        else:
            query = query.filter(level_id__isnull=True)

        existing = await query.first()
        if existing:
            return existing

        return await StudentExamAccess.create(
            student_id=student_id,
            teacher_id=teacher_id,
            subject_id=subject_id,
            level_id=level_id,
            granted_by_id=granted_by_id or teacher_id
        )

    @staticmethod
    async def batch_grant_access(
        student_ids: List[int],
        teacher_id: int,
        subject_id: int,
        level_id: Optional[int] = None,
        granted_by_id: int = None
    ) -> List[StudentExamAccess]:
        """批量授权多个学生访问试卷"""
        results = []
        for student_id in student_ids:
            access = await ExamAccessService.grant_access(
                student_id=student_id,
                teacher_id=teacher_id,
                subject_id=subject_id,
                level_id=level_id,
                granted_by_id=granted_by_id
            )
            results.append(access)
        return results

    @staticmethod
    async def revoke_access(access_id: int) -> bool:
        """撤销授权"""
        access = await StudentExamAccess.get_or_none(id=access_id)
        if access:
            await access.delete()
            return True
        return False

    @staticmethod
    async def get_student_accesses(student_id: int) -> List[StudentExamAccess]:
        """获取学生的所有授权"""
        return await StudentExamAccess.filter(student_id=student_id).prefetch_related("subject", "level", "teacher")

    @staticmethod
    async def get_teacher_granted_students(teacher_id: int) -> List[int]:
        """获取教师授权过的所有学生ID"""
        accesses = await StudentExamAccess.filter(teacher_id=teacher_id).distinct().values_list("student_id", flat=True)
        return list(accesses)

    @staticmethod
    async def get_accessible_exams(student_id: int) -> List[Exam]:
        """获取学生可访问的试卷"""
        # 获取学生的所有授权
        accesses = await StudentExamAccess.filter(student_id=student_id).prefetch_related("subject", "level").all()

        if not accesses:
            return []

        # 构建查询条件
        subject_ids = list(set(a.subject_id for a in accesses))

        # 按授权的科目和等级查询试卷
        query = Exam.filter(is_published=True, subject_id__in=subject_ids)

        exams = await query.prefetch_related("subject", "level").all()

        # 过滤：只保留学生有权限的等级
        accessible_exams = []
        for exam in exams:
            for access in accesses:
                if access.subject_id == exam.subject_id:
                    # 如果授权没有指定等级，或者试卷没有等级，或者授权的等级与试卷等级匹配
                    if access.level_id is None or exam.level_id is None or access.level_id == exam.level_id:
                        accessible_exams.append(exam)
                        break

        return accessible_exams

    @staticmethod
    async def get_student_subjects_with_levels(student_id: int) -> List[dict]:
        """获取学生可访问的科目和等级组合"""
        accesses = await StudentExamAccess.filter(student_id=student_id).prefetch_related("subject", "level").all()

        result = []
        for access in accesses:
            result.append({
                "subject": access.subject,
                "level": access.level
            })

        # 去重
        seen = set()
        unique = []
        for item in result:
            key = (item["subject"].id, item["level"].id if item["level"] else None)
            if key not in seen:
                seen.add(key)
                unique.append(item)

        return unique

    @staticmethod
    async def check_student_has_access(student_id: int, exam_id: int) -> bool:
        """检查学生是否有权访问某试卷"""
        exam = await Exam.get_or_none(id=exam_id)
        if not exam or not exam.is_published:
            return False

        accesses = await StudentExamAccess.filter(student_id=student_id, subject_id=exam.subject_id).all()

        for access in accesses:
            # 如果授权没有指定等级，或者试卷没有等级，或者授权的等级与试卷等级匹配
            if access.level_id is None or exam.level_id is None or access.level_id == exam.level_id:
                return True

        return False
