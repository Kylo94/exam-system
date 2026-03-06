# 生产环境部署指南

本文档详细说明如何使用 Docker Compose 部署在线答题系统到生产环境。

## 目录

1. [部署前准备](#部署前准备)
2. [快速部署](#快速部署)
3. [详细配置说明](#详细配置说明)
4. [数据库管理](#数据库管理)
5. [监控和维护](#监控和维护)
6. [故障排查](#故障排查)

---

## 部署前准备

### 1. 系统要求

**硬件要求：**
- CPU: 2 核心以上
- 内存: 4GB 以上
- 硬盘: 20GB 以上可用空间（SSD 推荐）

**软件要求：**
- 操作系统: Linux (Ubuntu 20.04+, CentOS 7+, Debian 10+)
- Docker: 20.10+
- Docker Compose: 1.29+
- 端口: 80, 443, 5002 需要可用

### 2. 安装 Docker 和 Docker Compose

#### Ubuntu / Debian

```bash
# 更新软件包索引
sudo apt-get update

# 安装依赖
sudo apt-get install -y \
    ca-certificates \
    curl \
    gnupg \
    lsb-release

# 添加 Docker 官方 GPG 密钥
sudo mkdir -p /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg

# 设置 Docker 仓库
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# 安装 Docker
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# 启动 Docker
sudo systemctl start docker
sudo systemctl enable docker

# 将当前用户添加到 docker 组（可选，避免每次使用 sudo）
sudo usermod -aG docker $USER
```

#### CentOS / RHEL

```bash
# 安装依赖
sudo yum install -y yum-utils

# 添加 Docker 仓库
sudo yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo

# 安装 Docker
sudo yum install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# 启动 Docker
sudo systemctl start docker
sudo systemctl enable docker
```

### 3. 克隆项目

```bash
# 克隆项目
git clone <repository-url>
cd 答题网站

# 或者进入现有项目目录
cd /path/to/答题网站
```

---

## 快速部署

### 一键部署

使用提供的部署脚本可以快速完成整个部署流程：

```bash
# 运行部署脚本
./scripts/deploy-production.sh
```

部署脚本会自动完成以下操作：
1. 检查系统依赖（Docker, Docker Compose）
2. 检查和创建环境配置文件
3. 创建必要的目录结构
4. 拉取 Docker 镜像
5. 构建应用镜像
6. 初始化数据库
7. 启动所有服务
8. 创建默认管理员账号
9. 显示访问信息

### 手动部署

如果需要更精细的控制，可以手动执行部署步骤：

```bash
# 1. 创建必要的目录
mkdir -p data/{postgres,redis,uploads,logs,nginx}
mkdir -p docker/nginx/{ssl,conf.d}
mkdir -p uploads logs

# 2. 复制并编辑环境配置
cp .env.production .env
nano .env  # 修改关键配置

# 3. 拉取镜像
docker-compose -f docker-compose.prod.yml pull

# 4. 构建应用镜像
docker-compose -f docker-compose.prod.yml build

# 5. 启动服务
docker-compose -f docker-compose.prod.yml up -d

# 6. 初始化数据库
docker-compose -f docker-compose.prod.yml exec web flask db upgrade

# 7. 创建管理员账号（如果不存在）
docker-compose -f docker-compose.prod.yml run --rm web python create_admin.py
```

---

## 详细配置说明

### 1. 环境变量配置

编辑 `.env` 文件，配置以下关键参数：

```bash
# 应用配置
FLASK_PORT=5002                      # Flask 应用端口
SECRET_KEY=your-random-secret-key      # 必须修改！
SECURITY_PASSWORD_SALT=your-salt      # 必须修改！

# 数据库配置
DB_PASSWORD=your-strong-password       # 必须修改！

# Gunicorn 配置
GUNICORN_WORKERS=4                   # Worker 进程数（CPU 核心 * 2 + 1）
GUNICORN_THREADS=2                    # 每个 Worker 的线程数

# AI API 配置（可选）
DEEPSEEK_API_KEY=your-api-key
OPENAI_API_KEY=your-api-key

# 邮件配置（可选）
MAIL_SERVER=smtp.example.com
MAIL_PORT=587
MAIL_USE_TLS=true
MAIL_USERNAME=your-email@example.com
MAIL_PASSWORD=your-email-password
MAIL_DEFAULT_SENDER=noreply@example.com
```

### 2. PostgreSQL 配置

PostgreSQL 配置文件位于 `docker/postgresql.conf`，主要配置项：

```ini
# 连接设置
max_connections = 100                # 最大连接数
shared_buffers = 256MB              # 共享缓冲区
effective_cache_size = 1GB          # 有效缓存大小

# WAL 设置
wal_buffers = 16MB
min_wal_size = 1GB
max_wal_size = 4GB

# 性能优化（SSD）
random_page_cost = 1.1
effective_io_concurrency = 200
```

### 3. Nginx 配置

Nginx 配置文件位于 `docker/nginx/conf.d/app.conf`，主要配置项：

```nginx
# 客户端请求大小限制
client_max_body_size 50M;

# 超时设置
proxy_connect_timeout 60s;
proxy_send_timeout 120s;
proxy_read_timeout 120s;

# Gzip 压缩
gzip on;
gzip_comp_level 6;
```

### 4. HTTPS 配置（可选）

如果需要启用 HTTPS，需要配置 SSL 证书：

```bash
# 创建证书目录
mkdir -p docker/nginx/ssl

# 放置证书文件
cp your-cert.pem docker/nginx/ssl/cert.pem
cp your-key.pem docker/nginx/ssl/key.pem

# 修改 Nginx 配置，取消 HTTPS 部分的注释
nano docker/nginx/conf.d/app.conf
```

---

## 数据库管理

### 1. 数据库备份

```bash
# 执行备份
./scripts/backup-db.sh

# 备份文件将保存到 backups/postgres/ 目录
# 文件命名格式: examdb_backup_YYYYMMDD_HHMMSS.sql.gz
```

### 2. 数据库恢复

```bash
# 解压备份文件
gunzip backups/postgres/examdb_backup_YYYYMMDD_HHMMSS.sql.gz

# 恢复数据库
cat backups/postgres/examdb_backup_YYYYMMDD_HHMMSS.sql | docker exec -i exam-postgres psql -U examuser -d examdb
```

### 3. 连接到数据库

```bash
# 使用 psql 连接
docker exec -it exam-postgres psql -U examuser -d examdb

# 查看数据库列表
\l

# 查看表列表
\dt

# 退出
\q
```

### 4. 数据库迁移

```bash
# 创建迁移
docker-compose -f docker-compose.prod.yml run --rm web flask db migrate -m "描述变更"

# 应用迁移
docker-compose -f docker-compose.prod.yml run --rm web flask db upgrade

# 回滚迁移
docker-compose -f docker-compose.prod.yml run --rm web flask db downgrade
```

### 5. 数据库性能监控

```sql
-- 查看表大小
SELECT * FROM get_table_sizes();

-- 查看慢查询
SELECT * FROM pg_stat_statements ORDER BY mean_exec_time DESC LIMIT 10;

-- 查看连接状态
SELECT * FROM pg_stat_activity;
```

---

## 监控和维护

### 1. 查看服务状态

```bash
# 查看所有容器状态
docker-compose -f docker-compose.prod.yml ps

# 查看资源使用情况
docker stats exam-web exam-postgres exam-redis exam-nginx
```

### 2. 查看日志

```bash
# 查看所有服务日志
docker-compose -f docker-compose.prod.yml logs -f

# 查看特定服务日志
docker-compose -f docker-compose.prod.yml logs -f web
docker-compose -f docker-compose.prod.yml logs -f db
docker-compose -f docker-compose.prod.yml logs -f nginx

# 查看最近 100 行日志
docker-compose -f docker-compose.prod.yml logs --tail=100 web
```

### 3. 服务管理

```bash
# 重启所有服务
docker-compose -f docker-compose.prod.yml restart

# 重启特定服务
docker-compose -f docker-compose.prod.yml restart web

# 停止所有服务
docker-compose -f docker-compose.prod.yml stop

# 启动所有服务
docker-compose -f docker-compose.prod.yml start

# 停止并删除容器
docker-compose -f docker-compose.prod.yml down

# 停止并删除容器和数据卷（谨慎使用）
docker-compose -f docker-compose.prod.yml down -v
```

### 4. 更新应用

```bash
# 拉取最新代码
git pull origin main

# 重新构建镜像
docker-compose -f docker-compose.prod.yml build web

# 重启服务
docker-compose -f docker-compose.prod.yml up -d

# 运行数据库迁移
docker-compose -f docker-compose.prod.yml run --rm web flask db upgrade
```

### 5. 设置自动备份

使用 cron 设置定时备份：

```bash
# 编辑 crontab
crontab -e

# 添加定时任务（每天凌晨 2 点备份）
0 2 * * * cd /path/to/答题网站 && ./scripts/backup-db.sh >> /var/log/exam-backup.log 2>&1
```

---

## 故障排查

### 1. 容器无法启动

**问题：** 容器启动失败

```bash
# 查看容器日志
docker-compose -f docker-compose.prod.yml logs <service-name>

# 检查端口占用
sudo netstat -tlnp | grep -E ':(80|443|5002)'

# 检查磁盘空间
df -h
```

### 2. 数据库连接失败

**问题：** 应用无法连接到数据库

```bash
# 检查数据库容器状态
docker ps | grep exam-postgres

# 检查数据库健康状态
docker exec exam-postgres pg_isready -U examuser -d examdb

# 检查环境变量
docker-compose -f docker-compose.prod.yml config | grep DATABASE_URL
```

### 3. 权限问题

**问题：** 文件上传失败或权限错误

```bash
# 检查目录权限
ls -la data/uploads

# 修改权限
chmod -R 755 data/uploads

# 修改所有者（如果需要）
chown -R www-data:www-data data/uploads
```

### 4. 内存不足

**问题：** 容器因内存不足被杀死

```bash
# 检查内存使用情况
free -h

# 减少 Gunicorn worker 数量
# 编辑 .env 文件
GUNICORN_WORKERS=2

# 重启服务
docker-compose -f docker-compose.prod.yml restart web
```

### 5. 数据库性能问题

**问题：** 数据库查询缓慢

```bash
# 连接到数据库
docker exec -it exam-postgres psql -U examuser -d examdb

# 查看慢查询
SELECT * FROM pg_stat_statements ORDER BY mean_exec_time DESC LIMIT 10;

# 分析表
ANALYZE;

# 重建索引
REINDEX DATABASE examdb;

# 清理数据库
VACUUM FULL;
```

---

## 安全建议

1. **修改默认配置**
   - 必须修改 `SECRET_KEY` 和 `SECURITY_PASSWORD_SALT`
   - 必须修改数据库密码
   - 禁用或修改默认管理员账号

2. **启用 HTTPS**
   - 配置有效的 SSL 证书
   - 强制 HTTPS 重定向

3. **防火墙配置**
   ```bash
   # 只开放必要端口
   sudo ufw allow 80/tcp
   sudo ufw allow 443/tcp
   sudo ufw enable
   ```

4. **定期备份**
   - 设置自动备份计划
   - 验证备份完整性
   - 测试恢复流程

5. **监控告警**
   - 配置日志监控
   - 设置资源使用告警
   - 定期检查服务健康状态

---

## 性能优化建议

1. **数据库优化**
   - 根据硬件配置调整 PostgreSQL 参数
   - 定期执行 `VACUUM` 和 `ANALYZE`
   - 为常用查询创建索引

2. **应用优化**
   - 调整 Gunicorn worker 数量
   - 启用 Redis 缓存
   - 使用 CDN 加速静态资源

3. **Nginx 优化**
   - 启用 Gzip 压缩
   - 调整缓存策略
   - 配置负载均衡（如有多台服务器）

---

## 联系支持

如遇部署问题，请：
1. 查看本文档的故障排查部分
2. 检查 Docker 容器日志
3. 提交 GitHub Issue
4. 联系技术支持团队
