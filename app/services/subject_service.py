"""科目服务"""
from typing import List, Dict, Any, Optional
from collections import defaultdict
from app.models.subject import Subject
from app.models.level import Level
from app.models.knowledge_point import KnowledgePoint
from app.models.question import Question
from app.services.exceptions import NotFoundException, ValidationException


class SubjectService:
    """科目业务逻辑"""

    @staticmethod
    async def get_subject_or_404(subject_id: int) -> Subject:
        """获取科目，不存在则抛异常"""
        subject = await Subject.get_or_none(id=subject_id)
        if not subject:
            raise NotFoundException("科目", subject_id)
        return subject

    @staticmethod
    async def create_subject(name: str, description: str = None, level_count: int = 3) -> Subject:
        """创建科目（同时创建等级）"""
        subject = await Subject.create(name=name, description=description)

        for i in range(1, level_count + 1):
            level_name = f"第{i}级"
            await Level.create(name=level_name, description=f"{level_name}难度", subject=subject)

        return subject

    @staticmethod
    async def update_subject(subject_id: int, name: str, description: str = None) -> Subject:
        """更新科目"""
        subject = await SubjectService.get_subject_or_404(subject_id)
        subject.name = name
        subject.description = description
        await subject.save()
        return subject

    @staticmethod
    async def delete_subject(subject_id: int) -> None:
        """删除科目"""
        subject = await SubjectService.get_subject_or_404(subject_id)
        await subject.delete()

    @staticmethod
    async def create_level(subject_id: int, name: str, description: str = None) -> Level:
        """为科目创建等级"""
        subject = await SubjectService.get_subject_or_404(subject_id)
        return await Level.create(name=name, description=description, subject=subject)

    @staticmethod
    async def update_level(level_id: int, name: str, description: str = None) -> Level:
        """更新等级"""
        level = await Level.get_or_none(id=level_id)
        if not level:
            raise NotFoundException("等级", level_id)
        level.name = name
        level.description = description
        await level.save()
        return level

    @staticmethod
    async def delete_level(level_id: int) -> None:
        """删除等级"""
        level = await Level.get_or_none(id=level_id)
        if not level:
            raise NotFoundException("等级", level_id)
        await level.delete()

    @staticmethod
    async def get_subjects_with_stats() -> List[Dict[str, Any]]:
        """获取所有科目及统计信息（优化：使用批量查询避免N+1）"""
        subjects = await Subject.all().order_by("name")
        if not subjects:
            return []

        subject_ids = [s.id for s in subjects]

        # 批量查询等级数量（按subject_id分组）
        level_counts = defaultdict(int)
        levels_raw = await Level.filter(subject_id__in=subject_ids).values_list("subject_id", flat=True)
        for sid in levels_raw:
            level_counts[sid] += 1

        # 批量查询知识点数量（按subject_id分组）
        kp_counts = defaultdict(int)
        kps_raw = await KnowledgePoint.filter(subject_id__in=subject_ids).values_list("subject_id", flat=True)
        for sid in kps_raw:
            kp_counts[sid] += 1

        # 组装结果
        result = []
        for s in subjects:
            result.append({
                "id": s.id,
                "name": s.name,
                "description": s.description,
                "level_count": level_counts.get(s.id, 0),
                "kp_count": kp_counts.get(s.id, 0)
            })
        return result

    @staticmethod
    async def get_levels_with_stats(subject_id: int) -> List[Dict[str, Any]]:
        """获取科目的等级及统计信息（优化：使用批量查询避免N+1）"""
        levels = await Level.filter(subject_id=subject_id).order_by("id")
        if not levels:
            return []

        level_ids = [l.id for l in levels]

        # 批量查询知识点数量（按level_id分组）
        kp_counts = defaultdict(int)
        kps_raw = await KnowledgePoint.filter(level_id__in=level_ids).values_list("level_id", flat=True)
        for lid in kps_raw:
            kp_counts[lid] += 1

        result = []
        for l in levels:
            result.append({
                "id": l.id,
                "name": l.name,
                "description": l.description,
                "knowledge_point_count": kp_counts.get(l.id, 0)
            })
        return result

    @staticmethod
    async def get_knowledge_points_with_stats(level_id: int) -> List[Dict[str, Any]]:
        """获取等级下的知识点及统计信息（优化：使用批量查询避免N+1）"""
        kps = await KnowledgePoint.filter(level_id=level_id).order_by("name")
        if not kps:
            return []

        kp_ids = [kp.id for kp in kps]

        # 批量查询题目数量（按knowledge_point_id分组）
        q_counts = defaultdict(int)
        qs_raw = await Question.filter(knowledge_point_id__in=kp_ids).values_list("knowledge_point_id", flat=True)
        for kpid in qs_raw:
            q_counts[kpid] += 1

        result = []
        for kp in kps:
            result.append({
                "id": kp.id,
                "name": kp.name,
                "description": kp.description,
                "display_id": kp.display_id,
                "subject_id": kp.subject_id,
                "level_id": kp.level_id,
                "question_count": q_counts.get(kp.id, 0)
            })
        return result