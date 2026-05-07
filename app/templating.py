"""
共享模板配置
"""
from fastapi.templating import Jinja2Templates

from app.config import settings

# 创建共享的Jinja2模板实例
templates = Jinja2Templates(directory="templates")
templates.env.globals["settings"] = settings


# 缓存的应用名称
_cached_app_name = None


def get_app_name():
    """获取应用名称，同步函数，返回缓存值"""
    global _cached_app_name
    return _cached_app_name if _cached_app_name is not None else settings.APP_NAME


async def load_app_name_async():
    """从数据库异步加载应用名称到缓存"""
    global _cached_app_name
    try:
        from app.models.system_settings import SystemSettings
        setting = await SystemSettings.get_or_none(key="app_name")
        if setting and setting.value:
            _cached_app_name = setting.value
            return
    except Exception:
        pass
    _cached_app_name = settings.APP_NAME


def clear_app_name_cache():
    """清除应用名称缓存"""
    global _cached_app_name
    _cached_app_name = None


def init_app_name_cache():
    """初始化应用名称缓存（同步版本）"""
    global _cached_app_name
    if _cached_app_name is None:
        _cached_app_name = settings.APP_NAME


# 添加为模板全局函数
templates.env.globals["get_app_name"] = get_app_name


def current_year():
    """返回当前年份"""
    from datetime import datetime
    return datetime.now().year


templates.env.globals["current_year"] = current_year
