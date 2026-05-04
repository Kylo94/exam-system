"""日志配置模块"""

import logging
import os
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
from datetime import datetime


def setup_logging(
    log_level: str = "DEBUG",
    log_dir: str = "logs",
    max_bytes: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5,
    when: str = "midnight",
    interval: int = 1
) -> None:
    """
    配置日志系统

    Args:
        log_level: 日志级别 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_dir: 日志目录
        max_bytes: 单个日志文件最大字节数
        backup_count: 保留的备份文件数量
        when: 轮转时间单位 (midnight, H, D, W0-W6)
        interval: 轮转间隔
    """
    # 创建日志目录
    os.makedirs(log_dir, exist_ok=True)

    # 转换为logging常量
    numeric_level = getattr(logging, log_level.upper(), logging.DEBUG)

    # 定义日志格式
    detailed_formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s:%(lineno)d | %(funcName)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    simple_formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # 控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(numeric_level)
    console_handler.setFormatter(simple_formatter)

    # 根日志记录器
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)

    # 避免重复添加处理器
    if root_logger.handlers:
        root_logger.handlers.clear()
    root_logger.addHandler(console_handler)

    # 应用日志 - 记录应用运行日志
    app_file_handler = RotatingFileHandler(
        filename=os.path.join(log_dir, "app.log"),
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8"
    )
    app_file_handler.setLevel(numeric_level)
    app_file_handler.setFormatter(detailed_formatter)

    app_logger = logging.getLogger("app")
    app_logger.setLevel(numeric_level)
    app_logger.addHandler(app_file_handler)
    app_logger.addHandler(console_handler)

    # 错误日志 - 只记录ERROR及以上
    error_file_handler = RotatingFileHandler(
        filename=os.path.join(log_dir, "error.log"),
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8"
    )
    error_file_handler.setLevel(logging.ERROR)
    error_file_handler.setFormatter(detailed_formatter)

    error_logger = logging.getLogger("error")
    error_logger.setLevel(logging.ERROR)
    error_logger.addHandler(error_file_handler)
    error_logger.addHandler(console_handler)

    # API访问日志
    access_file_handler = TimedRotatingFileHandler(
        filename=os.path.join(log_dir, "access.log"),
        when=when,
        interval=interval,
        backupCount=backup_count,
        encoding="utf-8"
    )
    access_file_handler.setLevel(logging.INFO)
    access_file_handler.setFormatter(detailed_formatter)

    access_logger = logging.getLogger("access")
    access_logger.setLevel(logging.INFO)
    access_logger.addHandler(access_file_handler)

    # AI日志 - 记录AI相关操作
    ai_file_handler = RotatingFileHandler(
        filename=os.path.join(log_dir, "ai.log"),
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8"
    )
    ai_file_handler.setLevel(logging.DEBUG)
    ai_file_handler.setFormatter(detailed_formatter)

    ai_logger = logging.getLogger("ai")
    ai_logger.setLevel(logging.DEBUG)
    ai_logger.addHandler(ai_file_handler)

    # 数据库日志
    db_file_handler = RotatingFileHandler(
        filename=os.path.join(log_dir, "database.log"),
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8"
    )
    db_file_handler.setLevel(logging.WARNING)
    db_file_handler.setFormatter(detailed_formatter)

    db_logger = logging.getLogger("database")
    db_logger.setLevel(logging.WARNING)
    db_logger.addHandler(db_file_handler)

    # 知识点评测日志
    kp_file_handler = RotatingFileHandler(
        filename=os.path.join(log_dir, "knowledge_point.log"),
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8"
    )
    kp_file_handler.setLevel(logging.DEBUG)
    kp_file_handler.setFormatter(detailed_formatter)

    kp_logger = logging.getLogger("knowledge_point")
    kp_logger.setLevel(logging.DEBUG)
    kp_logger.addHandler(kp_file_handler)

    # 配置第三方库的日志级别
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.error").setLevel(logging.ERROR)
    logging.getLogger("tortoise").setLevel(logging.WARNING)
    logging.getLogger("aiocache").setLevel(logging.WARNING)
    logging.getLogger("aiohttp").setLevel(logging.WARNING)

    root_logger.info(f"日志系统初始化完成 | 级别: {log_level} | 目录: {os.path.abspath(log_dir)}")


def get_logger(name: str = "app") -> logging.Logger:
    """
    获取日志记录器

    Args:
        name: 日志记录器名称 (app, error, access, ai, database, knowledge_point)

    Returns:
        日志记录器实例
    """
    return logging.getLogger(name)


class LoggerMixin:
    """日志混入类，其他类可以继承此来获得日志功能"""

    @property
    def logger(self) -> logging.Logger:
        """获取当前类的日志记录器"""
        name = f"{self.__class__.__module__}.{self.__class__.__name__}"
        return logging.getLogger(name)
