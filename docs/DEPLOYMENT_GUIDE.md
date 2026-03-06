# 📚 在线答题系统 - 部署指南

> **版本**: v1.1.0  
> **更新日期**: 2026-03-06  
> **部署方式**: Docker + Docker Compose

---

## 📋 目录

- [快速开始](#快速开始)
- [环境准备](#环境准备)
- [配置说明](#配置说明)
- [开发环境部署](#开发环境部署)
- [生产环境部署](#生产环境部署)
- [数据库配置](#数据库配置)
- [默认账号密码](#默认账号密码)
- [常用命令](#常用命令)
- [故障排查](#故障排查)
- [备份与恢复](#备份与恢复)

---

## 🚀 快速开始

### 一键部署（推荐）

```bash
# 1. 克隆仓库
git clone https://github.com/Kylo94/exam-system.git
cd exam-system

# 2. 开发环境一键启动
docker-compose up -d

# 3. 生产环境一键启动
docker-compose -f docker-compose.prod.yml up -d
```

### 访问应用

- **开发环境**: http://localhost:5002
- **生产环境**: http://localhost:80 (或配置的域名)

---

## 🛠️ 环境准备

### 系统要求

- **操作系统**: Linux / macOS / Windows (WSL2)
- **Docker**: 20.10+
- **Docker Compose**: 2.0+
- **内存**: 最小 2GB，推荐 4GB+
- **磁盘**: 最小 10GB 可用空间

### 安装 Docker

#### Ubuntu/Debian

```bash
# 安装 Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# 安装 Docker Compose
sudo apt-get install docker-compose-plugin

# 将当前用户添加到 docker 组
sudo usermod -aG docker $USER
newgrp docker
```

#### CentOS/RHEL

```bash
# 安装 Docker
sudo yum install -y yum-utils
sudo yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
sudo yum install docker-ce docker-ce-cli containerd.io

# 启动 Docker
sudo systemctl start docker
sudo systemctl enable docker

# 安装 Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

#### macOS

```bash
# 下载并安装 Docker Desktop
# https://www.docker.com/products/docker-desktop

# 或使用 Homebrew
brew install --cask docker
```

#### Windows

```bash
# 下载并安装 Docker Desktop
# https://www.docker.com/products/docker-desktop
# 确保 WSL2 已启用
```

### 验证安装

```bash
docker --version
docker-compose --version
docker ps
```

---

## ⚙️ 配置说明

### 环境变量配置

#### 1. 复制环境变量模板

```bash
# 开发环境
cp .env.example .env

# 生产环境
cp .env.production .env
```

#### 2. 修改配置文件

**`.env` 开发环境配置**：

```bash
# Flask 配置
FLASK_ENV=development
FLASK_PORT=5002
SECRET_KEY=dev-secret-key-change-in-production

# 数据库配置（开发环境使用 SQLite）
DATABASE_URL=sqlite:///exam_system.db

# 或者使用 PostgreSQL（需要安装数据库）
# DATABASE_URL=postgresql://examuser:exam_password_123456@localhost:5432/examdb

# Redis 配置（可选）
REDIS_URL=redis://localhost:6379/0

# AI API 配置
DEEPSEEK_API_KEY=your_deepseek_api_key
OPENAI_API_KEY=your_openai_api_key

# 文件上传配置
MAX_CONTENT_LENGTH=52428800  # 50MB
UPLOAD_FOLDER=uploads
```

**`.env.production` 生产环境配置**：

```bash
# Flask 配置
FLASK_ENV=production
FLASK_PORT=5002
SECRET_KEY=$(python -c "import secrets; print(secrets.token_hex(32))")

# 数据库配置
DB_PASSWORD=$(openssl rand -base64 32)

# Nginx 端口
NGINX_HTTP_PORT=80
NGINX_HTTPS_PORT=443

# Gunicorn 配置
GUNICORN_WORKERS=4
GUNICORN_THREADS=2

# 邮件配置（可选）
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=true
MAIL_USERNAME=your_email@gmail.com
MAIL_PASSWORD=your_app_password
MAIL_DEFAULT_SENDER=noreply@example.com
```

### Docker Compose 配置说明

#### 开发环境 (`docker-compose.yml`)

```yaml
services:
  db:        # PostgreSQL 数据库
  redis:     # Redis 缓存
  web:       # Flask Web 应用
  nginx:     # Nginx 反向代理
```

#### 生产环境 (`docker-compose.prod.yml`)

```yaml
services:
  db:        # PostgreSQL 数据库（性能优化）
  redis:     # Redis 缓存（性能优化）
  web:       # Flask Web 应用（Gunicorn）
  nginx:     # Nginx 反向代理
```

### 配置差异对比

| 配置项 | 开发环境 | 生产环境 |
|--------|----------|----------|
| 数据库 | SQLite 或 PostgreSQL | PostgreSQL（优化配置） |
| Web 服务器 | Flask 开发服务器 | Gunicorn |
| 反向代理 | 可选 | Nginx |
| 日志级别 | DEBUG | INFO |
| Worker 数量 | 1 | 4-8 |
| 资源限制 | 无 | CPU 2核，内存 2GB |
| 健康检查 | 简单 | 完善 |

---

## 💻 开发环境部署

### 方式一：使用 Docker Compose（推荐）

```bash
# 1. 创建并编辑 .env 文件
cp .env.example .env
vim .env

# 2. 启动服务
docker-compose up -d

# 3. 查看日志
docker-compose logs -f web

# 4. 访问应用
# http://localhost:5002
```

### 方式二：本地运行

```bash
# 1. 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/macOS
# 或
venv\Scripts\activate  # Windows

# 2. 安装依赖
pip install -r requirements.txt

# 3. 安装开发依赖
pip install -r requirements-dev.txt

# 4. 配置环境变量
cp .env.example .env
vim .env

# 5. 初始化数据库
flask db upgrade

# 6. 创建管理员账户
python create_admin.py

# 7. 启动开发服务器
flask run --host=0.0.0.0 --port=5002
```

### 开发环境特性

✅ **热重载**: 代码修改自动重启  
✅ **调试模式**: 显示详细错误信息  
✅ **SQLite 数据库**: 无需额外数据库服务  
✅ **简单配置**: 最小化配置即可运行  

---

## 🚢 生产环境部署

### 方式一：使用 Docker Compose（推荐）

```bash
# 1. 创建并编辑环境变量
cp .env.production .env
vim .env

# 2. 生成安全密钥
python -c "import secrets; print(secrets.token_hex(32))"

# 3. 创建必要目录
mkdir -p data/{postgres,redis,uploads,logs,nginx}

# 4. 启动服务
docker-compose -f docker-compose.prod.yml up -d

# 5. 初始化数据库
docker-compose -f docker-compose.prod.yml exec web flask db upgrade

# 6. 创建管理员账户
docker-compose -f docker-compose.prod.yml exec web python create_admin.py

# 7. 查看服务状态
docker-compose -f docker-compose.prod.yml ps
```

### 方式二：使用部署脚本

```bash
# 一键部署
./scripts/deploy-production.sh

# 查看日志
docker-compose -f docker-compose.prod.yml logs -f
```

### 生产环境特性

✅ **PostgreSQL 数据库**: 高性能、高可靠  
✅ **Gunicorn 服务器**: 生产级 WSGI 服务器  
✅ **Nginx 反向代理**: 负载均衡、SSL 支持  
✅ **Redis 缓存**: 会话存储、数据缓存  
✅ **健康检查**: 自动重启、故障恢复  
✅ **资源限制**: 防止资源耗尽  
✅ **日志管理**: 结构化日志、易于分析  

---

## 🗄️ 数据库配置

### PostgreSQL 配置

#### 1. 数据库连接信息

```yaml
# docker-compose.yml / docker-compose.prod.yml
environment:
  POSTGRES_DB: examdb
  POSTGRES_USER: examuser
  POSTGRES_PASSWORD: ${DB_PASSWORD:-exam_password_123456}
```

#### 2. 环境变量配置

```bash
# 开发环境
DATABASE_URL=postgresql://examuser:exam_password_123456@localhost:5432/examdb

# 生产环境
DATABASE_URL=postgresql://examuser:${DB_PASSWORD}@db:5432/examdb?sslmode=disable
```

#### 3. 数据库初始化

首次启动时会自动执行 `docker/init-db.sql`：

```sql
-- 安装扩展
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- 创建性能优化函数
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';
```

#### 4. 手动初始化数据库

```bash
# 进入 PostgreSQL 容器
docker-compose -f docker-compose.prod.yml exec db psql -U examuser -d examdb

# 或使用 psql 命令
psql -h localhost -p 5432 -U examuser -d examdb

# 执行初始化脚本
\i /docker-entrypoint-initdb.d/01-init-db.sql
```

#### 5. 数据库迁移

```bash
# 在容器中执行迁移
docker-compose -f docker-compose.prod.yml exec web flask db upgrade

# 或本地执行
flask db upgrade

# 查看迁移历史
flask db history

# 创建新迁移
flask db migrate -m "描述信息"
```

#### 6. 数据库性能优化

生产环境配置了以下优化参数：

```yaml
# docker-compose.prod.yml
POSTGRES_SHARED_BUFFERS: 256MB
POSTGRES_EFFECTIVE_CACHE_SIZE: 1GB
POSTGRES_MAINTENANCE_WORK_MEM: 64MB
POSTGRES_CHECKPOINT_COMPLETION_TARGET: 0.9
POSTGRES_WAL_BUFFERS: 16MB
POSTGRES_MAX_CONNECTIONS: 100
```

### SQLite 配置（开发环境）

#### 1. 数据库文件位置

```bash
# 默认位置
exam_system.db

# 或在 .env 中指定
DATABASE_URL=sqlite:///data/exam_system.db
```

#### 2. SQLite 限制

⚠️ **不适合生产环境使用**  
❌ 并发性能差  
❌ 不支持完整的事务  
❌ 不支持复杂的查询优化  

---

## 🔑 默认账号密码

### 初始管理员账户

**首次部署需要创建管理员账户**：

```bash
# 在容器中创建
docker-compose -f docker-compose.prod.yml exec web python create_admin.py

# 或本地创建
python create_admin.py
```

**输入示例**：
```
请输入管理员用户名: admin
请输入管理员邮箱: admin@example.com
请输入管理员密码: ********
请确认密码: ********
管理员账户创建成功！
```

### 系统默认配置

| 配置项 | 开发环境默认值 | 生产环境 | 说明 |
|--------|---------------|----------|------|
| 数据库用户 | `examuser` | `examuser` | PostgreSQL 用户 |
| 数据库密码 | `exam_password_123456` | **需自定义** | 生产环境必须修改 |
| 数据库名称 | `examdb` | `examdb` | PostgreSQL 数据库 |
| Redis 端口 | `6379` | `6379` | Redis 服务端口 |
| Flask 端口 | `5002` | `5002` | Web 应用端口 |
| Nginx HTTP 端口 | `80` | `80` | HTTP 访问端口 |
| Nginx HTTPS 端口 | `443` | `443` | HTTPS 访问端口 |

### 安全建议

⚠️ **生产环境必须修改以下配置**：

1. **数据库密码**
   ```bash
   # 生成强密码
   openssl rand -base64 32
   
   # 修改 .env 文件
   DB_PASSWORD=生成的密码
   ```

2. **Flask SECRET_KEY**
   ```bash
   # 生成密钥
   python -c "import secrets; print(secrets.token_hex(32))"
   
   # 修改 .env 文件
   SECRET_KEY=生成的密钥
   ```

3. **管理员密码**
   - 首次创建时使用强密码
   - 定期更换密码
   - 启用双因素认证（如支持）

---

## 📖 常用命令

### Docker Compose 命令

#### 开发环境

```bash
# 启动服务
docker-compose up -d

# 停止服务
docker-compose down

# 重启服务
docker-compose restart

# 查看日志
docker-compose logs -f web

# 查看服务状态
docker-compose ps

# 进入容器
docker-compose exec web bash
docker-compose exec db psql -U examuser -d examdb

# 更新镜像并重启
docker-compose pull
docker-compose up -d

# 清理数据（危险！）
docker-compose down -v
```

#### 生产环境

```bash
# 启动服务
docker-compose -f docker-compose.prod.yml up -d

# 停止服务
docker-compose -f docker-compose.prod.yml down

# 重启服务
docker-compose -f docker-compose.prod.yml restart web

# 查看日志
docker-compose -f docker-compose.prod.yml logs -f web

# 查看服务状态
docker-compose -f docker-compose.prod.yml ps

# 进入容器
docker-compose -f docker-compose.prod.yml exec web bash
docker-compose -f docker-compose.prod.yml exec db psql -U examuser -d examdb

# 重新构建镜像
docker-compose -f docker-compose.prod.yml build --no-cache

# 查看资源使用
docker stats
```

### 数据库命令

```bash
# 备份数据库
docker-compose exec db pg_dump -U examuser examdb > backup.sql

# 恢复数据库
docker-compose exec -T db psql -U examuser examdb < backup.sql

# 进入数据库
docker-compose exec db psql -U examuser -d examdb

# 查看数据库大小
docker-compose exec db psql -U examuser -d examdb -c "\l+"

# 查看表大小
docker-compose exec db psql -U examuser -d examdb -c "\dt+"
```

### 应用命令

```bash
# 数据库迁移
docker-compose exec web flask db upgrade

# 创建管理员
docker-compose exec web python create_admin.py

# 查看日志
docker-compose exec web tail -f logs/app.log

# 清理缓存
docker-compose exec redis redis-cli FLUSHDB
```

---

## 🔧 故障排查

### 常见问题

#### 1. 容器无法启动

**症状**：`docker-compose up` 失败

**解决方案**：
```bash
# 查看详细日志
docker-compose logs web

# 检查端口占用
lsof -i :5002

# 清理并重启
docker-compose down -v
docker-compose up -d
```

#### 2. 数据库连接失败

**症状**：`could not connect to server`

**解决方案**：
```bash
# 检查数据库是否启动
docker-compose ps db

# 等待数据库就绪
docker-compose exec db pg_isready

# 检查环境变量
docker-compose exec web env | grep DATABASE_URL
```

#### 3. 权限错误

**症状**：`Permission denied`

**解决方案**：
```bash
# 修复目录权限
sudo chown -R $USER:$USER data/
chmod -R 755 data/

# 修复上传目录权限
sudo chown -R $USER:$USER uploads/
chmod -R 755 uploads/
```

#### 4. 内存不足

**症状**：`Out of memory`

**解决方案**：
```bash
# 减少 Worker 数量
# 修改 docker-compose.prod.yml
GUNICORN_WORKERS: 2

# 或增加系统交换空间
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

#### 5. Nginx 502 Bad Gateway

**症状**：访问时返回 502 错误

**解决方案**：
```bash
# 检查 Web 服务是否启动
docker-compose ps web

# 检查 Nginx 配置
docker-compose exec nginx nginx -t

# 重启 Nginx
docker-compose restart nginx
```

### 日志查看

```bash
# 查看所有服务日志
docker-compose logs

# 查看 Web 应用日志
docker-compose logs -f web

# 查看数据库日志
docker-compose logs -f db

# 查看最近 100 行日志
docker-compose logs --tail=100 web

# 查看应用文件日志
docker-compose exec web tail -f logs/app.log
```

### 健康检查

```bash
# 检查容器健康状态
docker-compose ps

# 手动测试健康检查
curl http://localhost:5002/api/health

# 检查数据库健康
docker-compose exec db pg_isready -U examuser -d examdb

# 检查 Redis 健康
docker-compose exec redis redis-cli ping
```

---

## 💾 备份与恢复

### 数据库备份

#### 自动备份

```bash
# 使用备份脚本（每天自动执行）
./scripts/backup-db.sh

# 设置定时任务（每天凌晨 2 点）
crontab -e
# 添加以下行
0 2 * * * /path/to/exam-system/scripts/backup-db.sh
```

#### 手动备份

```bash
# 备份数据库到文件
docker-compose exec db pg_dump -U examuser examdb > backup_$(date +%Y%m%d_%H%M%S).sql

# 压缩备份
docker-compose exec db pg_dump -U examuser examdb | gzip > backup_$(date +%Y%m%d_%H%M%S).sql.gz
```

### 数据恢复

```bash
# 从 SQL 文件恢复
docker-compose exec -T db psql -U examuser examdb < backup_20240306_120000.sql

# 从压缩文件恢复
gunzip < backup_20240306_120000.sql.gz | docker-compose exec -T db psql -U examuser examdb
```

### 备份上传文件

```bash
# 备份上传文件
tar -czf uploads_backup_$(date +%Y%m%d_%H%M%S).tar.gz uploads/

# 恢复上传文件
tar -xzf uploads_backup_20240306_120000.tar.gz
```

### 完整备份脚本

```bash
#!/bin/bash
# 完整备份脚本

BACKUP_DIR="./backups"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

# 备份数据库
docker-compose exec db pg_dump -U examuser examdb | gzip > $BACKUP_DIR/db_$DATE.sql.gz

# 备份上传文件
tar -czf $BACKUP_DIR/uploads_$DATE.tar.gz uploads/

# 备份配置文件
cp .env $BACKUP_DIR/.env_$DATE

echo "备份完成: $BACKUP_DIR"
```

---

## 📚 相关文档

- [README.md](../README.md) - 项目介绍
- [CHANGELOG.md](../docs/CHANGELOG.md) - 版本更新记录
- [PRODUCTION_DEPLOYMENT.md](../docs/PRODUCTION_DEPLOYMENT.md) - 生产环境详细部署
- [API 文档](../docs/API.md) - API 接口文档（待补充）

---

## 🆘 获取帮助

### 官方文档

- [Docker 官方文档](https://docs.docker.com/)
- [Docker Compose 文档](https://docs.docker.com/compose/)
- [Flask 文档](https://flask.palletsprojects.com/)
- [Gunicorn 文档](https://docs.gunicorn.org/)

### 技术支持

- **GitHub**: https://github.com/Kylo94/exam-system
- **邮箱**: kylo94@163.com
- **QQ**: 903467977

### 问题反馈

如遇到问题，请提供以下信息：

1. 系统环境（OS、Docker 版本）
2. 错误信息或日志
3. 操作步骤
4. 配置文件（隐藏敏感信息）

---

## 📄 许可证

MIT License - 详见 [LICENSE](../LICENSE) 文件

---

**祝您部署顺利！** 🎉
