"""解析器共享常量和工具"""

# 有效题型标识
VALID_QUESTION_TYPES = [
    'single_choice', 'multiple_choice', 'true_false',
    'fill_blank', 'short_answer', 'coding'
]

# AI 返回的类型别名 → 内部标识
TYPE_ALIAS_MAP = {
    '单选题': 'single_choice',
    '多选题': 'multiple_choice',
    '判断题': 'true_false',
    '填空题': 'fill_blank',
    '简答题': 'short_answer',
    '编程题': 'coding',
    'judgment': 'true_false',
    'subjective': 'short_answer',
    'judge': 'true_false',
    'true-false': 'true_false',
    'choice': 'single_choice',
    'multiple': 'multiple_choice',
    'code': 'coding',
    'programming': 'coding',
}

# 题型显示名称
TYPE_DISPLAY = {
    'single_choice': '单选题',
    'multiple_choice': '多选题',
    'true_false': '判断题',
    'fill_blank': '填空题',
    'short_answer': '简答题',
    'coding': '编程题'
}


def sse_progress_msg(progress: int, message: str, level: str = "info",
                     current: int = 0, total: int = 0, details: dict = None,
                     task_id: str = None) -> str:
    """构建 SSE 进度消息"""
    import json
    data = {
        "progress": progress,
        "message": message,
        "level": level,
        "current": current,
        "total": total,
    }
    if task_id:
        data["task_id"] = task_id
    if details:
        data["details"] = details
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
