# 在线答题系统 v2.0.0

基于 Flask 的模块化、可扩展的在线答题系统，支持 Word 文档上传、AI 智能解析、多题型自动判卷。

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Docker](https://img.shields.io/badge/docker-latest-blue.svg)](https://hub.docker.com/)
[![Python](https://img.shields.io/badge/python-3.12+-green.svg)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/flask-3.0+-red.svg)](https://flask.palletsprojects.com/)

## 功能特性

### 核心功能
- **用户系统**：学生/教师/管理员角色权限管理、学生答题、成绩查看
- **教师管理**：教师注册、学生绑定申请、课程管理、成绩批改
- **试卷管理**：科目/等级分类、试卷列表、试题管理
- **试题解析**：Word 文档上传、AI/传统双解析器、图片提取
- **答题判卷**：多题型支持（单选/多选/判断/填空/主观/编程）、自动判卷
- **专项刷题**：按考点刷题、错题重做、历史记录
- **后台管理**：科目/等级管理、成绩统计、题目编辑、用户管理
- **数据可视化**：成绩统计图表、学习进度展示

### 技术特色
- **模块化架构**：清晰的分层设计（数据层、服务层、解析层、工具层、视图层、模板层）
- **类型安全**：完整的 Python 类型注解
- **代码规范**：单个函数不超过 50 行，高内聚低耦合
- **错误处理**：统一的异常处理机制
- **易于扩展**：插件式解析器、判卷器设计
- **容器化部署**：完整的 Docker 支持，一键部署
- **自动初始化**：启动时自动创建数据库和管理员账户

## 快速开始

### 前置要求
- Python 3.12+
- Docker 20.10+
- Docker Compose 2.0+

### Docker 部署（推荐）

#### 方式一：使用 docker-compose

```bash
# 1. 克隆仓库
git clone https://github.com/Kylo94/exam-system.git
cd exam-system

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env 修改 SECRET_KEY、ADMIN_PASSWORD、POSTGRES_PASSWORD 等敏感配置

# 3. 启动服务（自动初始化数据库和管理员）
docker-compose up -d

# 4. 访问应用
# http://localhost:5002
```

#### 方式二：使用 Docker Hub

```bash
# 命令行传递环境变量
docker run -d \
  -e SECRET_KEY="$(openssl rand -base64 32)" \
  -e ADMIN_USERNAME="admin" \
  -e ADMIN_PASSWORD="your-secure-password" \
  -e ADMIN_EMAIL="admin@example.com" \
  -e DATABASE_URL="postgresql://user:password@host:5432/dbname" \
  -p 5002:5002 \
  your-username/exam-system:latest
```

### 本地开发

```bash
# 1. 克隆仓库
git clone https://github.com/Kylo94/exam-system.git
cd exam-system

# 2. 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/macOS
# venv\Scripts\activate  # Windows

# 3. 安装依赖
pip install -r requirements.txt

# 4. 配置环境变量
cp .env.example .env
# 修改 .env: FLASK_ENV=development, FLASK_DEBUG=true, DATABASE_URL=sqlite:///instance/exam.db

# 5. 启动开发服务器（自动初始化数据库和管理员）
python run.py
```

### 系统初始化

系统首次启动时会自动完成以下操作：
- ✅ 检查并创建数据库表
- ✅ 执行数据库迁移
- ✅ 自动创建管理员账户

无需手动初始化！

## 默认账号密码

系统首次启动时会自动创建管理员账户：

**默认配置**：
- **管理员用户名**: `admin`（可通过 `ADMIN_USERNAME` 环境变量配置）
- **管理员密码**: `admin`（可通过 `ADMIN_PASSWORD` 环境变量配置）
- **管理员邮箱**: `admin@example.com`（可通过 `ADMIN_EMAIL` 环境变量配置）

**生产环境部署示例**：
```bash
# 方式一：命令行传递环境变量
docker run -d \
  -e SECRET_KEY="your-secret-key" \
  -e ADMIN_USERNAME="admin" \
  -e ADMIN_PASSWORD="your-secure-password" \
  -e ADMIN_EMAIL="admin@example.com" \
  -e DATABASE_URL="postgresql://user:pass@host:5432/db" \
  -p 5002:5002 \
  your-username/exam-system:latest

# 方式二：使用 .env 文件
cat > .env << 'EOF'
SECRET_KEY=your-secret-key
ADMIN_USERNAME=admin
ADMIN_PASSWORD=your-password
ADMIN_EMAIL=admin@example.com
DATABASE_URL=postgresql://user:password@db:5432/examdb
POSTGRES_PASSWORD=your-db-password
EOF

docker run -d --env-file .env -p 5002:5002 your-username/exam-system:latest
```

⚠️ **生产环境必须通过环境变量修改默认密码！**

## 环境变量配置

### 必需配置（生产环境）

| 变量名 | 说明 | 默认值 | 是否必需 |
|--------|------|--------|---------|
| `SECRET_KEY` | Flask 安全密钥 | dev-secret-key | 是 |
| `ADMIN_PASSWORD` | 管理员密码 | admin | 是 |
| `POSTGRES_PASSWORD` | PostgreSQL 密码 | exam_password_123456 | Docker部署 |
| `DATABASE_URL` | 数据库连接 | sqlite:///instance/exam.db | 是 |

### 可选配置

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `ADMIN_USERNAME` | 管理员用户名 | admin |
| `ADMIN_EMAIL` | 管理员邮箱 | admin@example.com |
| `FLASK_ENV` | Flask 环境 | production |
| `FLASK_DEBUG` | 调试模式 | false |
| `LOG_LEVEL` | 日志级别 | INFO |
| `MAX_CONTENT_LENGTH` | 最大上传大小 | 52428800 (50MB) |

完整配置请参考 `.env.example` 文件。

## 文档

- **[部署指南](docs/部署指南.md)** - 完整的部署说明（推荐）
  - Docker 部署
  - Docker Hub 部署
  - 本地开发
  - 生产环境部署
  - 环境变量配置
  - 数据库管理
  - 故障排查

- **[文档说明](docs/文档说明.md)** - 文档目录索引

- **[更新日志](docs/更新日志.md)** - 版本历史和更新内容

- **[数据库迁移指南](docs/数据库迁移指南.md)** - 数据库管理

## 技术栈

### 后端
- **Python 3.12+** - 核心语言
- **Flask 3.0+** - Web 框架
- **SQLAlchemy 2.0+** - ORM
- **Flask-Migrate** - 数据库迁移
- **Flask-Login** - 用户认证
- **python-docx** - Word 文档解析
- **PyPDF2** - PDF 文档解析
- **Pillow** - 图片处理
- **bcrypt** - 密码加密

### 前端
- **Bootstrap 5.3** - CSS 框架
- **Jinja2** - 模板引擎
- **Chart.js** - 数据可视化
- **jQuery** - DOM 操作

### 数据库
- **PostgreSQL** - 生产环境数据库
- **SQLite** - 开发环境数据库

### 容器化
- **Docker** - 容器平台
- **Docker Compose** - 容器编排

## 项目结构

```
exam-system/
├── app/                    # 应用主目录
│   ├── models/            # 数据模型
│   ├── routes/            # 路由视图
│   ├── services/          # 业务逻辑
│   ├── parsers/           # 试题解析器
│   ├── graders/           # 判卷器
│   ├── utils/             # 工具函数
│   ├── extensions.py     # Flask 扩展
│   └── __init__.py        # 应用工厂
├── templates/             # 模板文件
├── static/                # 静态文件
├── migrations/            # 数据库迁移
├── uploads/               # 上传文件
├── logs/                  # 日志文件
├── docs/                  # 文档
├── docker-compose.yml     # Docker Compose 配置
├── Dockerfile             # Docker 镜像配置
├── .env.example           # 环境变量模板
├── requirements.txt       # Python 依赖
└── run.py                 # 应用入口
```

## 常用命令

### Docker 部署

```bash
# 启动服务
docker-compose up -d

# 停止服务
docker-compose stop

# 重启服务
docker-compose restart

# 查看日志
docker-compose logs -f web

# 进入容器
docker-compose exec web bash

# 查看运行状态
docker-compose ps

# 删除容器和卷
docker-compose down -v
```

### 本地开发

```bash
# 启动开发服务器
python run.py

# 运行测试
pytest

# 数据库迁移
flask db upgrade

# 查看日志
tail -f logs/exam_system.log
```

## 系统要求

### 开发环境
- Python 3.12+
- 2GB 内存
- 10GB 磁盘空间

### 生产环境
- Docker 20.10+
- 4GB+ 内存
- 20GB+ 磁盘空间
- Linux (Ubuntu 20.04+, CentOS 7+)

## 开发指南

### 代码规范
- 单个函数不超过 50 行
- 完整的类型注解
- 遵循 PEP 8 规范
- 使用 Git Flow 工作流

### 提交规范
```
feat: 新功能
fix: 修复bug
docs: 文档更新
style: 代码格式
refactor: 重构
test: 测试相关
chore: 构建/工具
```

## 故障排查

### 常见问题

**1. 容器无法启动**
```bash
# 查看日志
docker-compose logs web

# 检查端口占用
lsof -i :5002
```

**2. 数据库连接失败**
```bash
# 检查数据库状态
docker-compose ps db

# 查看数据库日志
docker-compose logs db
```

**3. 管理员无法登录**
```bash
# 检查管理员账户
docker-compose exec web python -c "
from app import create_app
from app.models.user import User
app = create_app()
with app.app_context():
    admin = User.get_by_username('admin')
    print(f'管理员存在: {admin.username}, 邮箱: {admin.email}')
"
```

更多问题请查看 [部署指南](docs/部署指南.md)。

## 贡献指南

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'feat: Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

## 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件

## 联系方式

- **作者**: Kylo94
- **Email**: your-email@example.com
- **GitHub**: https://github.com/Kylo94/exam-system

## 更新日志

### v2.0.0 (2026-03-11)
- ✨ 实现自动初始化功能
- ✨ 支持通过环境变量配置管理员
- ✨ 支持从 Docker Hub 部署
- 🐛 修复数据库初始化问题
- 📝 更新部署文档
- ♻️ 重构 README.md，去除过时配置

### v1.1.0
- 添加 AI 智能判卷功能
- 优化用户体验
- 性能优化

### v1.0.0
- 初始版本发布
- 基础功能实现
