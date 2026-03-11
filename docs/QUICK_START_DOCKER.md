# Docker 快速部署指南

本指南提供使用 Docker 快速部署在线答题系统的步骤。

## 前置要求

- Docker 20.10+
- Docker Compose 1.29+
- 至少 2GB RAM
- 至少 10GB 可用磁盘空间

## 快速开始

### 1. 克隆代码仓库

```bash
git clone <your-repository-url>
cd <repository-name>
```

### 2. 配置环境变量

```bash
# 复制环境变量模板
cp .env.production.example .env.production

# 编辑配置文件
nano .env.production
```

**重要配置项**：

```bash
# 必须修改的安全配置
SECRET_KEY=请使用 python -c "import secrets; print(secrets.token_hex(32))" 生成

# 数据库密码（建议修改）
POSTGRES_PASSWORD=your_secure_password

# 应用端口（可选）
FLASK_PORT=5002
```

生成安全的 SECRET_KEY：

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

### 3. 构建并启动服务

#### 使用部署脚本（推荐）

```bash
# 使用生产部署脚本
./scripts/deploy-production.sh
```

#### 手动部署

```bash
# 1. 构建镜像
docker-compose -f docker-compose.prod.yml build

# 2. 启动服务
docker-compose -f docker-compose.prod.yml up -d

# 3. 查看日志
docker-compose -f docker-compose.prod.yml logs -f
```

### 4. 验证部署

```bash
# 检查服务状态
docker-compose -f docker-compose.prod.yml ps

# 检查日志
docker-compose -f docker-compose.prod.yml logs web
```

### 5. 访问应用

打开浏览器访问：`http://localhost:5002`

默认管理员账户：
- 用户名: `admin`
- 密码: `admin`
- ⚠️ **重要**: 首次登录后请立即修改密码！

## 数据库迁移

### 自动迁移

使用 `docker-compose.prod.yml`，容器启动时会自动执行迁移。

### 手动迁移

```bash
# 执行迁移
docker-compose -f docker-compose.prod.yml run --rm web flask db upgrade

# 检查迁移状态
docker-compose -f docker-compose.prod.yml run --rm web flask db current
```

### 查看迁移历史

```bash
docker-compose -f docker-compose.prod.yml run --rm web flask db history
```

## 管理员账户

### 创建管理员账户

```bash
# 使用专用脚本
docker-compose -f docker-compose.prod.yml run --rm web python create_admin.py
```

### 首次登录

1. 访问 `http://localhost:5002/auth/login`
2. 使用默认账户登录：`admin` / `admin`
3. 立即修改密码！

## 常用命令

### 服务管理

```bash
# 启动服务
docker-compose -f docker-compose.prod.yml up -d

# 停止服务
docker-compose -f docker-compose.prod.yml down

# 重启服务
docker-compose -f docker-compose.prod.yml restart

# 重启指定服务
docker-compose -f docker-compose.prod.yml restart web
```

### 日志查看

```bash
# 查看所有服务日志
docker-compose -f docker-compose.prod.yml logs -f

# 查看指定服务日志
docker-compose -f docker-compose.prod.yml logs -f web

# 查看最近 100 行日志
docker-compose -f docker-compose.prod.yml logs --tail=100 web
```

### 数据库管理

```bash
# 进入数据库
docker-compose -f docker-compose.prod.yml exec db psql -U examuser -d examdb

# 备份数据库
docker-compose -f docker-compose.prod.yml exec db pg_dump -U examuser examdb > backup.sql

# 恢复数据库
docker-compose -f docker-compose.prod.yml exec -T db psql -U examuser examdb < backup.sql

# 使用备份脚本
./scripts/backup-db.sh
```

### 进入容器

```bash
# 进入 Web 容器
docker-compose -f docker-compose.prod.yml exec web bash

# 进入数据库容器
docker-compose -f docker-compose.prod.yml exec db bash
```

## 更新应用

```bash
# 1. 拉取最新代码
git pull

# 2. 重新构建镜像
docker-compose -f docker-compose.prod.yml build web

# 3. 重启服务
docker-compose -f docker-compose.prod.yml up -d web

# 4. 执行数据库迁移（如果有）
docker-compose -f docker-compose.prod.yml run --rm web flask db upgrade
```

## 故障排查

### 服务无法启动

```bash
# 检查日志
docker-compose -f docker-compose.prod.yml logs

# 检查服务状态
docker-compose -f docker-compose.prod.yml ps

# 查看容器详情
docker inspect exam-web-prod
```

### 数据库连接失败

```bash
# 检查数据库是否运行
docker-compose -f docker-compose.prod.yml exec db pg_isready

# 测试数据库连接
docker-compose -f docker-compose.prod.yml exec web python -c "
from app import create_app
app = create_app('production')
with app.app_context():
    from app.extensions import db
    print('数据库连接成功:', db.engine.url)
"
```

### 迁移失败

```bash
# 查看当前迁移版本
docker-compose -f docker-compose.prod.yml run --rm web flask db current

# 查看迁移历史
docker-compose -f docker-compose.prod.yml run --rm web flask db history

# 手动执行迁移
docker-compose -f docker-compose.prod.yml run --rm web flask db upgrade
```

### 端口冲突

如果端口 5002 被占用，修改 `.env.production`：

```bash
FLASK_PORT=8080  # 改为其他端口
```

## 清理

### 停止并删除容器

```bash
docker-compose -f docker-compose.prod.yml down
```

### 删除容器和数据卷（⚠️ 会删除所有数据！）

```bash
docker-compose -f docker-compose.prod.yml down -v
```

### 清理未使用的镜像

```bash
docker system prune -a
```

## 安全建议

1. **修改默认密码**: 首次部署后立即修改所有默认密码
2. **使用 HTTPS**: 在生产环境配置 SSL 证书
3. **限制访问**: 使用防火墙限制数据库端口访问
4. **定期备份**: 设置定时任务备份数据库
5. **监控日志**: 定期检查应用和数据库日志
6. **更新依赖**: 定期更新 Docker 镜像和依赖包

## 性能优化

### 调整 Gunicorn 配置

编辑 `docker-compose.prod.yml`，根据服务器资源调整：

```yaml
command: >
  gunicorn --bind 0.0.0.0:5002
           --workers 4        # CPU 核心数
           --threads 2        # 每个 worker 的线程数
           --timeout 120
           --worker-class sync
```

### 数据库优化

编辑 `docker-compose.prod.yml`，调整 PostgreSQL 配置：

```yaml
db:
  command: >
    postgres
    -c max_connections=200
    -c shared_buffers=512MB  # 增加 shared_buffers
    -c effective_cache_size=2GB
    -c maintenance_work_mem=256MB
```

## 支持

如遇问题，请参考：
- [数据库迁移指南](DATABASE_MIGRATION.md)
- [完整部署指南](DEPLOYMENT.md)
- [项目 README](../README.md)
