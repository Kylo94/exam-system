"""
ID生成器服务 - 为不同实体分配不同的ID段
"""
from typing import Literal

# ID分段配置
ID_RANGES = {
    "admin": (1, 999),
    "teacher": (1001, 1999),
    "student": (2001, 2999),
    "exam": (3001, 3999),
    "subject": (4001, 4999),
    "level": (5001, 5999),
    "knowledge_point": (6001, 6999),
    "question": (7001, 7999),
    "submission": (8001, 8999),
    "ai_config": (9001, 9999),
}


def get_display_id(actual_id: int, entity_type: str) -> int:
    """
    根据实际ID和实体类型计算显示ID

    Args:
        actual_id: 数据库中的实际ID
        entity_type: 实体类型 (admin, teacher, student, exam, subject, level, knowledge_point, question, submission, ai_config)

    Returns:
        显示用的ID
    """
    if entity_type == "admin":
        return actual_id  # 管理员ID保持原样

    range_start, _ = ID_RANGES.get(entity_type, (1, 999))
    base = range_start - 1

    return actual_id + base


def parse_display_id(display_id: int, entity_type: str) -> int:
    """
    将显示ID转换回实际ID

    Args:
        display_id: 显示用的ID
        entity_type: 实体类型

    Returns:
        数据库中的实际ID
    """
    if entity_type == "admin":
        return display_id  # 管理员ID保持原样

    range_start, _ = ID_RANGES.get(entity_type, (1, 999))
    base = range_start - 1

    return display_id - base


def get_id_prefix(entity_type: str) -> str:
    """
    获取ID前缀
    """
    prefixes = {
        "admin": "A",
        "teacher": "T",
        "student": "S",
        "exam": "E",
        "subject": "C",
        "level": "L",
        "knowledge_point": "K",
        "question": "Q",
        "submission": "B",
        "ai_config": "AI",
    }
    return prefixes.get(entity_type, "X")


def format_display_id(actual_id: int, entity_type: str) -> str:
    """
    格式化显示ID，包含前缀

    Args:
        actual_id: 数据库中的实际ID
        entity_type: 实体类型

    Returns:
        格式化后的ID字符串，如 "S2001" 表示学生ID
    """
    prefix = get_id_prefix(entity_type)
    display_id = get_display_id(actual_id, entity_type)
    return f"{prefix}{display_id}"
