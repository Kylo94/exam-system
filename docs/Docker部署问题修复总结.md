# Docker 部署问题修复总结

## 问题概述

在检查正式发布版本的 Docker 部署方式时，发现多个与数据库迁移和管理员创建相关的问题。

## 发现的问题

### 🔴 严重问题

#### 1. 缺少 `docker-compose.prod.yml` 文件
**位置**: `scripts/deploy-production.sh` 多处引用
**影响**: 生产部署脚本无法正常工作
**修复**: 创建了 `docker-compose.prod.yml` 文件

#### 2. 数据库迁移流程不完整
**位置**: `docker-compose.yml` 和 `Dockerfile`
**影响**:
- 容器启动时不会自动执行数据库迁移
- 没有检查数据库连接状态
- 迁移失败会导致应用无法启动
**修复**:
- 创建了 `entrypoint.sh` 脚本
- 添加了数据库就绪检查
- 容器启动时自动执行 `flask db upgrade`

#### 3. 管理员创建流程错误
**位置**: `scripts/deploy-production.sh` 第 164-193 行
**影响**:
- 导入路径错误：`from app.models.user import User`（应该是 `from app.models import User`）
- 没有检查数据库连接
**修复**:
- 修改为使用 `create_admin.py` 脚本
- 添加数据库连接检查

#### 4. 数据迁移脚本未在容器启动时执行
**位置**: `Dockerfile`
**影响**: 模型变更后无法自动更新数据库结构
**修复**: 在 `entrypoint.sh` 中添加自动迁移执行

### 🟡 中等问题

#### 5. 缺少 `.env.production.example` 文件
**位置**: `scripts/deploy-production.sh` 第 62 行
**影响**: 部署脚本无法复制配置模板
**修复**: 创建了 `.env.production.example` 文件

#### 6. 数据库密码安全性问题
**位置**: `docker-compose.yml` 第 46 行
**影响**: 硬编码了不安全的默认密钥
**修复**: 在 `.env.production.example` 中添加安全提示

#### 7. 迁移文件被 gitignore
**位置**: `.gitignore` 第 60-61 行
**影响**: 迁移文件无法提交到版本控制
**修复**: 修改 `.gitignore`，只忽略 `*.pyc` 文件

### 🟢 轻微问题

#### 8. 启动脚本中使用 `db.create_all()`
**位置**: `start_prod_simple.sh` 第 39 行
**影响**: 生产环境不应该使用 `db.create_all()`
**修复**: 添加了 `flask db upgrade` 命令

## 解决方案

### 1. 新增文件

#### `docker-compose.prod.yml`
生产环境的 Docker Compose 配置文件，包含：
- PostgreSQL 数据库服务
- Flask Web 应用服务
- 自动化的数据库迁移和管理员创建
- 健康检查配置

#### `entrypoint.sh`
容器启动脚本，负责：
- 等待数据库就绪
- 执行数据库迁移
- 创建管理员账户
- 启动应用服务

#### `.env.production.example`
生产环境配置模板，包含：
- 所有必要的配置项
- 安全配置提示
- 默认值说明

#### `docs/DATABASE_MIGRATION.md`
数据库迁移完整指南，包含：
- 开发环境迁移
- 生产环境迁移
- 数据库更换（SQLite → PostgreSQL）
- 管理员账户迁移
- 故障排查
- 备份与恢复

#### `docs/QUICK_START_DOCKER.md`
Docker 快速部署指南，包含：
- 前置要求
- 快速开始步骤
- 数据库迁移
- 管理员账户
- 常用命令
- 故障排查
- 性能优化

#### `scripts/migrate-db.sh`
数据库迁移脚本，提供：
- 交互式迁移界面
- 数据库连接检查
- 迁移版本对比
- 迁移历史查看

### 2. 修改文件

#### `Dockerfile`
- 添加 `netcat-traditional` 用于数据库连接检查
- 设置 `entrypoint.sh` 为启动入口
- 保持原有的健康检查配置

#### `.gitignore`
- 修改迁移文件忽略规则（只忽略 `.pyc`）
- 添加 `.env.production` 到忽略列表
- 添加 Docker 数据卷目录到忽略列表

#### `scripts/deploy-production.sh`
- 修复管理员创建逻辑
- 使用 `create_admin.py` 脚本
- 移除内联 Python 代码

#### `start_prod_simple.sh`
- 添加 `flask db upgrade` 命令
- 保持数据库初始化逻辑

## 测试建议

### 1. 测试容器启动
```bash
# 构建镜像
docker-compose -f docker-compose.prod.yml build

# 启动服务
docker-compose -f docker-compose.prod.yml up -d

# 查看日志
docker-compose -f docker-compose.prod.yml logs -f web
```

### 2. 测试数据库迁移
```bash
# 检查迁移状态
docker-compose -f docker-compose.prod.yml run --rm web flask db current

# 查看迁移历史
docker-compose -f docker-compose.prod.yml run --rm web flask db history
```

### 3. 测试管理员创建
```bash
# 运行管理员创建脚本
docker-compose -f docker-compose.prod.yml run --rm web python create_admin.py

# 检查数据库中的用户
docker-compose -f docker-compose.prod.yml exec db psql -U examuser -d examdb -c "SELECT username, email, role FROM users;"
```

### 4. 测试数据库更换

从 SQLite 迁移到 PostgreSQL：
1. 备份 SQLite 数据
2. 创建 PostgreSQL 数据库
3. 使用 pgloader 迁移数据
4. 更新环境变量
5. 执行迁移

### 5. 测试应用功能
- 访问 `http://localhost:5002`
- 使用管理员账户登录
- 创建考试和题目
- 学生答题
- 查看结果

## 部署流程

### 首次部署

1. **准备环境**
   ```bash
   cp .env.production.example .env.production
   nano .env.production
   ```

2. **启动服务**
   ```bash
   ./scripts/deploy-production.sh
   ```

3. **验证部署**
   ```bash
   docker-compose -f docker-compose.prod.yml ps
   docker-compose -f docker-compose.prod.yml logs web
   ```

### 更新部署

1. **拉取代码**
   ```bash
   git pull
   ```

2. **重新构建**
   ```bash
   docker-compose -f docker-compose.prod.yml build web
   ```

3. **重启服务**
   ```bash
   docker-compose -f docker-compose.prod.yml up -d web
   ```

4. **执行迁移**
   ```bash
   docker-compose -f docker-compose.prod.yml run --rm web flask db upgrade
   ```

## 注意事项

### 安全
- ⚠️ 务必修改 `SECRET_KEY`
- ⚠️ 务必修改数据库密码
- ⚠️ 首次登录后立即修改管理员密码
- ⚠️ 生产环境使用 HTTPS

### 备份
- 定期备份数据库
- 保留迁移文件
- 备份配置文件

### 监控
- 监控日志文件
- 监控磁盘空间
- 监控服务状态

## 总结

通过以上修复，Docker 部署流程现已完善：
- ✅ 自动化的数据库迁移
- ✅ 自动化的管理员创建
- ✅ 完整的配置管理
- ✅ 详细的文档说明
- ✅ 可靠的错误处理

用户现在可以安全、可靠地使用 Docker 部署在线答题系统。
