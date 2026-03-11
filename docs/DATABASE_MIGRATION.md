# 数据库迁移指南

本文档说明如何在不同环境间进行数据库迁移。

## 概述

本系统使用 Flask-Migrate (基于 Alembic) 进行数据库版本管理和迁移。

## 开发环境迁移

### 创建新的迁移文件

当修改了数据库模型后，创建新的迁移文件：

```bash
flask db migrate -m "描述此次变更"
```

### 应用迁移

```bash
flask db upgrade
```

### 回滚迁移

```bash
flask db downgrade
```

## 生产环境迁移

### 使用 Docker Compose

#### 方式一：自动迁移（推荐）

使用 `docker-compose.prod.yml`，容器启动时会自动执行迁移：

```bash
docker-compose -f docker-compose.prod.yml up -d web
```

#### 方式二：手动迁移

```bash
# 1. 确保迁移文件已同步
git pull

# 2. 运行迁移
docker-compose -f docker-compose.prod.yml run --rm web flask db upgrade
```

### 使用非 Docker 环境

```bash
# 1. 设置环境变量
export FLASK_ENV=production

# 2. 运行迁移
flask db upgrade
```

## 数据库更换（迁移到 PostgreSQL）

### 从 SQLite 迁移到 PostgreSQL

#### 步骤 1: 备份 SQLite 数据

```bash
# 使用 SQLite 导出数据
sqlite3 instance/exam_system.db .dump > backup.sql
```

#### 步骤 2: 创建 PostgreSQL 数据库

```bash
# 连接到 PostgreSQL
psql -U postgres -d postgres

# 创建数据库和用户
CREATE DATABASE examdb;
CREATE USER examuser WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE examdb TO examuser;
\q
```

#### 步骤 3: 使用迁移工具

**方式一：使用 pgloader（推荐）**

```bash
# 安装 pgloader
brew install pgloader  # macOS
# 或
apt-get install pgloader  # Ubuntu/Debian

# 运行迁移
pgloader sqlite://instance/exam_system.db postgresql://examuser:password@localhost/examdb
```

**方式二：手动导出导入**

```bash
# 1. 从 SQLite 导出为 CSV
sqlite3 instance/exam_system.db <<EOF
.headers on
.mode csv
.output users.csv
SELECT * FROM users;
.output exams.csv
SELECT * FROM exams;
.output questions.csv
SELECT * FROM questions;
.output submissions.csv
SELECT * FROM submissions;
.output answers.csv
SELECT * FROM answers;
EOF

# 2. 导入到 PostgreSQL
psql -U examuser -d examdb <<EOF
\copy users FROM 'users.csv' CSV HEADER
\copy exams FROM 'exams.csv' CSV HEADER
\copy questions FROM 'questions.csv' CSV HEADER
\copy submissions FROM 'submissions.csv' CSV HEADER
\copy answers FROM 'answers.csv' CSV HEADER
EOF
```

#### 步骤 4: 更新配置

编辑 `.env.production`：

```bash
DATABASE_URL=postgresql://examuser:your_password@localhost:5432/examdb
```

#### 步骤 5: 验证迁移

```bash
# 连接到 PostgreSQL 验证
psql -U examuser -d examdb

# 检查表
\dt

# 检查数据
SELECT COUNT(*) FROM users;
SELECT COUNT(*) FROM exams;
```

## 管理员账户迁移

管理员账户会在数据库迁移后自动创建（如果不存在）：

```bash
# 使用专用脚本
python create_admin.py

# 或在 Docker 中
docker-compose -f docker-compose.prod.yml run --rm web python create_admin.py
```

默认管理员账户：
- 用户名: `admin`
- 密码: `admin`
- 邮箱: `admin@example.com`

⚠️ **重要**: 首次登录后请立即修改密码！

## 故障排查

### 迁移失败

#### 检查迁移版本

```bash
# 查看当前迁移版本
flask db current

# 查看迁移历史
flask db history
```

#### 重置迁移（仅开发环境）

```bash
# 删除所有迁移（谨慎使用！）
rm -rf migrations/versions/*

# 重新生成初始迁移
flask db init
flask db migrate -m "Initial migration"
flask db upgrade
```

### 数据库连接失败

#### 检查环境变量

```bash
echo $DATABASE_URL
```

#### 测试连接

```bash
# PostgreSQL
psql -U examuser -d examdb

# SQLite
sqlite3 instance/exam_system.db
```

## 最佳实践

1. **始终备份**: 在进行迁移前备份数据库
2. **测试迁移**: 在开发/测试环境先验证迁移
3. **版本控制**: 将迁移文件纳入 Git 管理
4. **逐步迁移**: 对于大型数据库，考虑分批迁移
5. **文档记录**: 记录每次迁移的变更内容

## 备份与恢复

### 备份

```bash
# PostgreSQL
docker-compose -f docker-compose.prod.yml exec db pg_dump -U examuser examdb > backup_$(date +%Y%m%d_%H%M%S).sql

# SQLite
cp instance/exam_system.db backup_$(date +%Y%m%d_%H%M%S).db
```

### 恢复

```bash
# PostgreSQL
docker-compose -f docker-compose.prod.yml exec -T db psql -U examuser examdb < backup_file.sql

# SQLite
cp backup_file.db instance/exam_system.db
```
