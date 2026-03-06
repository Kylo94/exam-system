# 使用官方 Python 镜像
FROM python:3.12-slim

# 设置工作目录
WORKDIR /app

# 设置环境变量
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FLASK_APP=run.py \
    FLASK_ENV=production

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    curl \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .

# 安装 Python 依赖
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir gunicorn

# 复制应用代码
COPY app/ ./app/
COPY migrations/ ./migrations/
COPY static/ ./static/
COPY templates/ ./templates/
COPY requirements.txt run.py wsgi.py config.py ./

# 创建必要的目录
RUN mkdir -p uploads logs instance

# 设置权限
RUN chmod -R 755 uploads logs instance

# 暴露端口
EXPOSE 5002

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c \"from app import create_app; app = create_app('production'); test_client = app.test_client(); test_client.get('/').status_code == 200\" || exit 1

# 启动应用
CMD ["gunicorn", "--bind", "0.0.0.0:5002", "--workers", "2", "--threads", "2", "--timeout", "120", "--access-logfile", "-", "--error-logfile", "-", "--log-level", "info", "wsgi:app"]
