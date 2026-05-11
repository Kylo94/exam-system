"""上传进度管理服务"""
import time
import uuid
from asyncio import Event
from typing import Dict, Optional


class UploadTask:
    """上传任务"""

    def __init__(self, task_id: str):
        self.task_id = task_id
        self.cancel_event = Event()
        self.progress = 0
        self.message = ""
        self.level = "info"
        self.current = 0
        self.total = 0
        self.completed = False
        self.details = None
        self._result = None
        self.created_at = time.time()

    def to_dict(self) -> Dict:
        return {
            "task_id": self.task_id,
            "progress": self.progress,
            "message": self.message,
            "level": self.level,
            "current": self.current,
            "total": self.total,
            "completed": self.completed,
            "details": self.details,
        }

    def to_sse_data(self) -> str:
        import json
        return json.dumps(self.to_dict())


class UploadService:
    """上传任务管理服务"""

    _tasks: Dict[str, UploadTask] = {}

    _TASK_TTL = 3600  # 1小时

    @classmethod
    def _cleanup_old_tasks(cls):
        """清理超过 TTL 的旧任务"""
        now = time.time()
        stale = [
            tid for tid, t in cls._tasks.items()
            if t.completed and now - t.created_at > cls._TASK_TTL
        ]
        for tid in stale:
            cls._tasks.pop(tid, None)

    @classmethod
    def create_task(cls) -> str:
        """创建新任务"""
        cls._cleanup_old_tasks()
        task_id = str(uuid.uuid4())[:8]
        cls._tasks[task_id] = UploadTask(task_id)
        return task_id

    @classmethod
    def get_task(cls, task_id: str) -> Optional[UploadTask]:
        """获取任务"""
        return cls._tasks.get(task_id)

    @classmethod
    def get_cancel_event(cls, task_id: str) -> Optional[Event]:
        """获取任务的取消事件"""
        task = cls._tasks.get(task_id)
        return task.cancel_event if task else None

    @classmethod
    def update_progress(
        cls,
        task_id: str,
        progress: int,
        message: str = "",
        level: str = "info",
        current: int = 0,
        total: int = 0,
        details=None
    ) -> bool:
        """更新任务进度"""
        task = cls._tasks.get(task_id)
        if not task:
            return False

        task.progress = progress
        task.message = message
        task.level = level
        task.current = current
        task.total = total
        task.details = details
        return True

    @classmethod
    def complete_task(cls, task_id: str, result=None) -> bool:
        """标记任务完成"""
        task = cls._tasks.get(task_id)
        if not task:
            return False

        task.completed = True
        task.progress = 100
        task.message = "完成"
        task._result = result
        return True

    @classmethod
    def cancel_task(cls, task_id: str) -> bool:
        """取消任务"""
        task = cls._tasks.get(task_id)
        if not task:
            return False

        task.cancel_event.set()
        task.completed = True
        task.progress = 0
        task.message = "已取消"
        task.level = "warning"
        return True

    @classmethod
    def remove_task(cls, task_id: str):
        """移除任务"""
        cls._tasks.pop(task_id, None)

    @classmethod
    def get_task_status(cls, task_id: str) -> Optional[Dict]:
        """获取任务状态"""
        task = cls._tasks.get(task_id)
        return task.to_dict() if task else None

    @classmethod
    def is_cancelled(cls, task_id: str) -> bool:
        """检查任务是否已取消"""
        task = cls._tasks.get(task_id)
        return task.cancel_event.is_set() if task else True