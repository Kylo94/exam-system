# 在线答题系统部署指南

本文档提供完整的部署指南，涵盖 Docker、Linux 和 Windows 三种部署方式。

## 目录

- [前置要求](#前置要求)
- [环境变量配置](#环境变量配置)
- [Docker 部署](#docker-部署)
- [Linux 部署](#linux-部署)
- [Windows 部署](#windows-部署)
- [生产环境优化](#生产环境优化)
- [故障排查](#故障排查)

---

## 前置要求

### 通用要求
- Python 3.9 或更高版本
- PostgreSQL 13+ (生产环境推荐) 或 SQLite (开发环境)
- 至少 2GB RAM
- 至少 10GB 可用磁盘空间

### Docker 部署要求
- Docker 20.10+
- Docker Compose 1.29+

### Linux 部署要求
- Linux 发行版 (Ubuntu 20.04+, CentOS 8+, Debian 10+)
- Nginx 1.18+
- Gunicorn 20.0+

### Windows 部署要求
- Windows 10/11 或 Windows Server 2019+
- IIS 10+ (可选，用于反向代理)

---

## 环境变量配置

### 1. 复制环境变量模板

```bash
cp .env.example .env
```

### 2. 编辑 `.env` 文件

```bash
# 应用配置
FLASK_ENV=production
SECRET_KEY=your-secret-key-here-change-in-production
APP_NAME=在线答题系统 v3.0
FLASK_HOST=0.0.0.0
FLASK_PORT=5002

# 数据库配置 (生产环境使用 PostgreSQL)
DATABASE_URL=postgresql://user:password@localhost:5432/examdb
# 开发环境可使用: DATABASE_URL=sqlite:///exam_system.db

# 文件上传配置
MAX_CONTENT_LENGTH=16777216
UPLOAD_FOLDER=uploads

# AI 配置 (可选)
DEEPSEEK_API_KEY=your-deepseek-api-key
DEEPSEEK_BASE_URL=https://api.deepseek.com
OPENAI_API_KEY=your-openai-api-key
OPENAI_BASE_URL=https://api.openai.com/v1
```

### 3. 生成安全的 SECRET_KEY

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

---

## Docker 部署

### 方式一：使用 Docker Compose (推荐)

#### 1. 创建 `docker-compose.yml`

```yaml
version: '3.8'

services:
  db:
    image: postgres:14
    container_name: exam-postgres
    environment:
      POSTGRES_DB: examdb
      POSTGRES_USER: examuser
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    networks:
      - exam-network
    restart: unless-stopped

  web:
    build: .
    container_name: exam-web
    ports:
      - "5002:5002"
    environment:
      FLASK_ENV: production
      DATABASE_URL: postgresql://examuser:${DB_PASSWORD}@db:5432/examdb
      SECRET_KEY: ${SECRET_KEY}
      DEEPSEEK_API_KEY: ${DEEPSEEK_API_KEY}
    volumes:
      - ./uploads:/app/uploads
      - ./logs:/app/logs
    depends_on:
      - db
    networks:
      - exam-network
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5002/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  nginx:
    image: nginx:alpine
    container_name: exam-nginx
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./ssl:/etc/nginx/ssl:ro
    depends_on:
      - web
    networks:
      - exam-network
    restart: unless-stopped

volumes:
  postgres_data:

networks:
  exam-network:
    driver: bridge
```

#### 2. 创建 `Dockerfile`

```dockerfile
# 使用官方 Python 镜像
FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .

# 安装 Python 依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY . .

# 创建必要的目录
RUN mkdir -p uploads logs instance

# 设置环境变量
ENV FLASK_APP=run.py
ENV FLASK_ENV=production

# 暴露端口
EXPOSE 5002

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5002/health || exit 1

# 启动应用
CMD ["gunicorn", "--bind", "0.0.0.0:5002", "--workers", "4", "--timeout", "120", "wsgi:app"]
```

#### 3. 创建 `.dockerignore`

```
.git
.gitignore
.venv
venv/
__pycache__/
*.pyc
*.pyo
*.pyd
.Python
*.so
*.egg
*.egg-info/
dist/
build/
.env
*.log
logs/
instance/
uploads/
tests/
docs/
migrations/
```

#### 4. 创建 `nginx.conf`

```nginx
events {
    worker_connections 1024;
}

http {
    upstream web {
        server web:5002;
    }

    # 限制上传文件大小
    client_max_body_size 20M;

    server {
        listen 80;
        server_name your-domain.com;

        # 重定向到 HTTPS
        return 301 https://$server_name$request_uri;
    }

    server {
        listen 443 ssl http2;
        server_name your-domain.com;

        # SSL 证书配置
        ssl_certificate /etc/nginx/ssl/fullchain.pem;
        ssl_certificate_key /etc/nginx/ssl/privkey.pem;
        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_ciphers HIGH:!aNULL:!MD5;

        # 日志
        access_log /var/log/nginx/access.log;
        error_log /var/log/nginx/error.log;

        location / {
            proxy_pass http://web;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        # 静态文件
        location /static {
            proxy_pass http://web;
            expires 30d;
        }

        location /uploads {
            proxy_pass http://web;
            expires 30d;
        }
    }
}
```

#### 5. 构建和启动

```bash
# 构建镜像
docker-compose build

# 启动服务
docker-compose up -d

# 查看日志
docker-compose logs -f web

# 初始化数据库
docker-compose exec web flask db upgrade

# 创建管理员账号
docker-compose exec web python create_admin.py
```

#### 6. 管理命令

```bash
# 停止服务
docker-compose down

# 停止并删除数据
docker-compose down -v

# 查看服务状态
docker-compose ps

# 重启服务
docker-compose restart

# 进入容器
docker-compose exec web bash
```

### 方式二：直接使用 Docker 命令

```bash
# 构建镜像
docker build -t exam-system:v3.0 .

# 运行容器
docker run -d \
  --name exam-web \
  -p 5002:5002 \
  -v $(pwd)/uploads:/app/uploads \
  -v $(pwd)/logs:/app/logs \
  --env-file .env \
  exam-system:v3.0

# 查看日志
docker logs -f exam-web

# 停止容器
docker stop exam-web

# 删除容器
docker rm exam-web
```

---

## Linux 部署

### Ubuntu/Debian 部署

#### 1. 安装系统依赖

```bash
# 更新系统
sudo apt update && sudo apt upgrade -y

# 安装 Python 和 pip
sudo apt install -y python3.11 python3-pip python3-venv

# 安装 PostgreSQL
sudo apt install -y postgresql postgresql-contrib

# 安装 Nginx
sudo apt install -y nginx

# 安装系统依赖
sudo apt install -y build-essential libpq-dev curl
```

#### 2. 安装 Gunicorn

```bash
sudo pip3 install gunicorn
```

#### 3. 配置 PostgreSQL

```bash
# 切换到 postgres 用户
sudo -u postgres psql

# 创建数据库和用户
CREATE DATABASE examdb;
CREATE USER examuser WITH ENCRYPTED PASSWORD 'your-password';
GRANT ALL PRIVILEGES ON DATABASE examdb TO examuser;
\q

# 测试连接
psql -h localhost -U examuser -d examdb
```

#### 4. 创建项目目录和虚拟环境

```bash
# 创建项目目录
sudo mkdir -p /opt/exam-system
sudo chown $USER:$USER /opt/exam-system
cd /opt/exam-system

# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

#### 5. 配置环境变量

```bash
# 复制环境变量文件
cp .env.example .env

# 编辑环境变量
nano .env
```

#### 6. 初始化数据库

```bash
# 设置 Flask 应用
export FLASK_APP=run.py

# 初始化数据库迁移（首次部署）
flask db upgrade

# 创建管理员账号
python create_admin.py
```

#### 7. 配置 Gunicorn Systemd 服务

创建服务文件 `/etc/systemd/system/exam-system.service`:

```ini
[Unit]
Description=在线答题系统 Gunicorn 服务
After=network.target postgresql.service

[Service]
Type=notify
User=www-data
Group=www-data
RuntimeDirectory=exam-system
WorkingDirectory=/opt/exam-system
Environment="PATH=/opt/exam-system/venv/bin"
Environment="FLASK_ENV=production"
ExecStart=/opt/exam-system/venv/bin/gunicorn \
    --bind 127.0.0.1:5002 \
    --workers 4 \
    --worker-class sync \
    --worker-connections 1000 \
    --timeout 120 \
    --keepalive 5 \
    --max-requests 1000 \
    --max-requests-jitter 50 \
    --access-logfile /var/log/exam-system/access.log \
    --error-logfile /var/log/exam-system/error.log \
    --log-level info \
    wsgi:app
ExecReload=/bin/kill -s HUP $MAINPID
KillMode=mixed
TimeoutStopSec=5
PrivateTmp=true
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

创建日志目录并设置权限：

```bash
sudo mkdir -p /var/log/exam-system
sudo chown www-data:www-data /var/log/exam-system
sudo chown -R www-data:www-data /opt/exam-system
```

启动服务：

```bash
# 重载 systemd 配置
sudo systemctl daemon-reload

# 启动服务
sudo systemctl start exam-system

# 设置开机自启
sudo systemctl enable exam-system

# 查看服务状态
sudo systemctl status exam-system

# 查看日志
sudo journalctl -u exam-system -f
```

#### 8. 配置 Nginx 反向代理

创建 Nginx 配置文件 `/etc/nginx/sites-available/exam-system`:

```nginx
upstream exam_backend {
    server 127.0.0.1:5002;
}

# 限制上传文件大小
client_max_body_size 20M;

server {
    listen 80;
    server_name your-domain.com;

    # 访问日志
    access_log /var/log/nginx/exam-access.log;
    error_log /var/log/nginx/exam-error.log;

    # 静态文件缓存
    location /static/ {
        alias /opt/exam-system/app/static/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    # 上传文件
    location /uploads/ {
        alias /opt/exam-system/uploads/;
        expires 30d;
    }

    # 主应用
    location / {
        proxy_pass http://exam_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # 超时设置
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 120s;

        # 缓冲设置
        proxy_buffering on;
        proxy_buffer_size 4k;
        proxy_buffers 8 4k;
        proxy_busy_buffers_size 8k;
    }
}
```

启用配置：

```bash
# 创建符号链接
sudo ln -s /etc/nginx/sites-available/exam-system /etc/nginx/sites-enabled/

# 测试配置
sudo nginx -t

# 重启 Nginx
sudo systemctl restart nginx
```

#### 9. 配置 SSL (Let's Encrypt)

```bash
# 安装 Certbot
sudo apt install -y certbot python3-certbot-nginx

# 获取 SSL 证书
sudo certbot --nginx -d your-domain.com

# 自动续期
sudo certbot renew --dry-run
```

#### 10. 防火墙配置

```bash
# 允许 HTTP 和 HTTPS
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# 启用防火墙
sudo ufw enable

# 查看状态
sudo ufw status
```

### CentOS/RHEL 部署

```bash
# 安装系统依赖
sudo yum install -y python3.11 python3-pip postgresql-server nginx

# 初始化 PostgreSQL
sudo postgresql-setup initdb
sudo systemctl start postgresql
sudo systemctl enable postgresql

# 其他步骤与 Ubuntu 类似
```

---

## Windows 部署

### 方式一：使用 WSL2 (推荐)

WSL2 提供 Windows 下的 Linux 环境，推荐使用此方式。

#### 1. 启用 WSL2

以管理员身份打开 PowerShell：

```powershell
# 启用 WSL
dism.exe /online /enable-feature /featurename:Microsoft-Windows-Subsystem-Linux /all /norestart
dism.exe /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart

# 重启电脑
```

#### 2. 安装 Ubuntu

打开 Microsoft Store，搜索并安装 Ubuntu 22.04 LTS。

#### 3. 配置 WSL2

打开 PowerShell：

```powershell
# 设置 WSL2 为默认版本
wsl --set-default-version 2
```

#### 4. 在 WSL 中部署

```bash
# 打开 Ubuntu
wsl

# 更新系统
sudo apt update && sudo apt upgrade -y

# 按照 Linux 部署步骤进行
```

### 方式二：使用 IIS + FastCGI

#### 1. 安装 Python

从 https://www.python.org/downloads/ 下载并安装 Python 3.11。

勾选 "Add Python to PATH" 选项。

#### 2. 安装 wfastcgi

```powershell
# 在管理员 PowerShell 中运行
pip install wfastcgi
wfastcgi-enable
```

#### 3. 配置应用

```powershell
# 创建项目目录
mkdir C:\exam-system
cd C:\exam-system

# 创建虚拟环境
python -m venv venv
.\venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt
```

#### 4. 配置 web.config

创建 `web.config` 文件：

```xml
<?xml version="1.0" encoding="utf-8"?>
<configuration>
  <appSettings>
    <add key="WSGI_HANDLER" value="wsgi.app" />
    <add key="PYTHONPATH" value="C:\exam-system" />
    <add key="WSGI_LOG" value="C:\exam-system\logs\wfastcgi.log" />
  </appSettings>
  <system.webServer>
    <handlers>
      <add name="PythonHandler" path="*" verb="*" modules="FastCgiModule"
           scriptProcessor="C:\Python311\python.exe|C:\exam-system\venv\Lib\site-packages\wfastcgi.py"
           resourceType="Unspecified" requireAccess="Script" />
    </handlers>
  </system.webServer>
</configuration>
```

#### 5. 配置 IIS

1. 打开 IIS 管理器
2. 添加网站
   - 网站名称: exam-system
   - 物理路径: C:\exam-system
   - 端口: 80
3. 启用 FastCGI
   - 打开"处理程序映射"
   - 添加模块映射
   - 请求路径: *
   - 模块: FastCgiModule
   - 可执行文件: C:\Python311\python.exe|C:\exam-system\venv\Lib\site-packages\wfastcgi.py

### 方式三：使用 Windows 服务

#### 1. 安装 NSSM (Non-Sucking Service Manager)

下载并解压 NSSM: https://nssm.cc/download

#### 2. 安装服务

```powershell
# 以管理员身份运行
cd C:\path\to\nssm
nssm install ExamSystem C:\exam-system\venv\Scripts\gunicorn.exe
```

#### 3. 配置服务参数

```
Application:
  - Path: C:\exam-system\venv\Scripts\gunicorn.exe
  - Startup directory: C:\exam-system
  - Arguments: --bind 0.0.0.0:5002 --workers 4 wsgi:app

Details:
  - Display name: 在线答题系统
  - Description: Flask 在线答题系统

Log on:
  - Log on as: Local System

I/O:
  - Stdout: C:\exam-system\logs\service.log
  - Stderr: C:\exam-system\logs\error.log
```

#### 4. 启动服务

```powershell
nssm start ExamSystem
```

### 方式四：使用 Docker Desktop

在 Windows 上安装 Docker Desktop，然后按照 [Docker 部署](#docker-部署) 章节操作。

---

## 生产环境优化

### 1. 数据库优化

#### PostgreSQL 配置优化

编辑 `/etc/postgresql/14/main/postgresql.conf`:

```ini
# 连接配置
max_connections = 100
shared_buffers = 256MB
effective_cache_size = 1GB

# 查询优化
work_mem = 4MB
maintenance_work_mem = 64MB

# WAL 配置
wal_buffers = 16MB
checkpoint_completion_target = 0.9

# 日志配置
log_destination = 'stderr'
logging_collector = on
log_directory = 'pg_log'
log_filename = 'postgresql-%Y-%m-%d_%H%M%S.log'
log_min_duration_statement = 1000
```

重启 PostgreSQL：

```bash
sudo systemctl restart postgresql
```

### 2. Gunicorn 优化

根据服务器配置调整 worker 数量：

```bash
# CPU 核心数 + (2-4)
workers = (2 * CPU核心数) + 1

# 每个 worker 的线程数
threads = 2-4

# 示例配置 (4核CPU)
gunicorn --workers 9 --threads 4 --worker-class gthread wsgi:app
```

### 3. 文件上传优化

修改 `config.py`:

```python
# 增加上传大小限制
MAX_CONTENT_LENGTH = 52428800  # 50MB

# 配置上传目录
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
```

### 4. 缓存配置

安装 Redis 用于缓存：

```bash
# 安装 Redis
sudo apt install -y redis-server

# 启动 Redis
sudo systemctl start redis-server
sudo systemctl enable redis-server
```

### 5. 日志轮转配置

创建 `/etc/logrotate.d/exam-system`:

```
/var/log/exam-system/*.log {
    daily
    rotate 30
    compress
    delaycompress
    notifempty
    create 0640 www-data www-data
    sharedscripts
    postrotate
        systemctl reload exam-system > /dev/null 2>&1 || true
    endscript
}
```

### 6. 监控配置

#### 安装 Prometheus 和 Grafana (可选)

```bash
# 安装 Prometheus
docker run -d --name prometheus \
  -p 9090:9090 \
  -v /opt/prometheus.yml:/etc/prometheus/prometheus.yml \
  prom/prometheus

# 安装 Grafana
docker run -d --name grafana \
  -p 3000:3000 \
  grafana/grafana
```

### 7. 自动备份

创建备份脚本 `/opt/scripts/backup.sh`:

```bash
#!/bin/bash

# 配置
BACKUP_DIR="/opt/backups"
DATE=$(date +%Y%m%d_%H%M%S)
DB_NAME="examdb"
DB_USER="examuser"
DB_PASSWORD="your-password"

# 创建备份目录
mkdir -p $BACKUP_DIR

# 数据库备份
pg_dump -h localhost -U $DB_USER $DB_NAME | gzip > $BACKUP_DIR/db_$DATE.sql.gz

# 文件备份
tar -czf $BACKUP_DIR/uploads_$DATE.tar.gz /opt/exam-system/uploads

# 删除7天前的备份
find $BACKUP_DIR -type f -mtime +7 -delete

echo "Backup completed: $DATE"
```

设置定时任务：

```bash
# 编辑 crontab
crontab -e

# 添加每天凌晨2点备份
0 2 * * * /opt/scripts/backup.sh >> /var/log/backup.log 2>&1
```

---

## 故障排查

### 常见问题

#### 1. 数据库连接失败

```bash
# 检查 PostgreSQL 状态
sudo systemctl status postgresql

# 检查数据库连接
psql -h localhost -U examuser -d examdb

# 检查防火墙
sudo ufw status
```

#### 2. 502 Bad Gateway

```bash
# 检查 Gunicorn 状态
sudo systemctl status exam-system

# 检查端口监听
sudo netstat -tlnp | grep 5002

# 查看 Gunicorn 日志
sudo tail -f /var/log/exam-system/error.log
```

#### 3. 静态文件 404

```bash
# 检查文件权限
sudo chown -R www-data:www-data /opt/exam-system/app/static

# 检查 Nginx 配置
sudo nginx -t
```

#### 4. 文件上传失败

```bash
# 检查上传目录权限
sudo chown -R www-data:www-data /opt/exam-system/uploads
sudo chmod -R 755 /opt/exam-system/uploads

# 检查 Nginx 上传大小限制
# client_max_body_size 20M;
```

#### 5. Docker 容器无法启动

```bash
# 查看容器日志
docker logs exam-web

# 进入容器调试
docker exec -it exam-web bash

# 检查容器状态
docker ps -a
```

### 日志查看

```bash
# 应用日志
sudo tail -f /var/log/exam-system/error.log

# Nginx 访问日志
sudo tail -f /var/log/nginx/exam-access.log

# Nginx 错误日志
sudo tail -f /var/log/nginx/exam-error.log

# 系统日志
sudo journalctl -u exam-system -f
```

### 性能分析

```bash
# 检查 CPU 和内存使用
htop

# 检查数据库性能
psql -U examuser -d examdb -c "SELECT * FROM pg_stat_activity;"

# 检查网络连接
sudo netstat -an | grep 5002
```

---

## 更新和升级

### 更新应用代码

```bash
# 备份数据
python backup.py

# 拉取最新代码
git pull origin main

# 安装依赖更新
pip install -r requirements.txt --upgrade

# 数据库迁移
flask db upgrade

# 重启服务
sudo systemctl restart exam-system
```

### 版本回滚

```bash
# 查看提交历史
git log --oneline

# 回滚到指定版本
git checkout <commit-hash>

# 数据库回滚
flask db downgrade

# 重启服务
sudo systemctl restart exam-system
```

---

## 安全建议

1. **定期更新系统**: 保持操作系统和依赖包最新
2. **使用强密码**: 数据库、SECRET_KEY 等使用复杂密码
3. **启用 HTTPS**: 使用 SSL/TLS 加密传输
4. **限制文件上传**: 验证文件类型和大小
5. **配置防火墙**: 只开放必要端口
6. **定期备份**: 每日自动备份数据库和文件
7. **监控日志**: 及时发现异常访问
8. **使用 SELinux**: 在支持的系统上启用 SELinux

---

## 技术支持

如遇到部署问题，请：

1. 查看本文档的故障排查章节
2. 检查相关日志文件
3. 提交 Issue 到项目仓库
4. 联系技术支持团队

---

## 许可证

MIT License
