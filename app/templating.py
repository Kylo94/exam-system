"""
共享模板配置
"""
from fastapi.templating import Jinja2Templates
from app.config import settings

# 创建共享的Jinja2模板实例
templates = Jinja2Templates(directory="templates")
templates.env.globals["settings"] = settings
