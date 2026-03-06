# 在线答题系统 v1.1.0

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

## 快速开始

### 前置要求
- Python 3.12+
- Docker 20.10+
- Docker Compose 2.0+

### 一键部署

#### 开发环境
```bash
# 1. 克隆仓库
git clone https://github.com/Kylo94/exam-system.git
cd exam-system

# 2. 配置环境变量
cp .env.example .env

# 3. 构建镜像
./scripts/build-image.sh dev

# 4. 启动服务
docker-compose up -d

# 5. 访问应用
# http://localhost:5002
```

#### 生产环境
```bash
# 1. 配置生产环境变量
cp .env.production .env
# 编辑 .env 文件，修改密钥和密码

# 2. 构建镜像
./scripts/build-image.sh prod

# 3. 启动服务
docker-compose -f docker-compose.prod.yml up -d

# 4. 初始化数据库
docker-compose -f docker-compose.prod.yml exec web flask db upgrade

# 5. 创建管理员账户
docker-compose -f docker-compose.prod.yml exec web python create_admin.py

# 6. 访问应用
# http://localhost:80
```

### 本地开发

```bash
# 1. 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/macOS
# venv\Scripts\activate  # Windows

# 2. 安装依赖
pip install -r requirements.txt

# 3. 配置环境变量
cp .env.example .env

# 4. 初始化数据库
flask db upgrade

# 5. 创建管理员
python create_admin.py

# 6. 启动开发服务器
flask run --host=0.0.0.0 --port=5002
```

## 文档

- **[部署指南](docs/DEPLOYMENT_GUIDE.md)** - 完整的部署说明（推荐）
  - 环境准备
  - 开发/生产环境部署
  - 数据库配置
  - 默认账号密码
  - 常用命令
  - 故障排查

- **[生产环境部署](docs/PRODUCTION_DEPLOYMENT.md)** - 生产环境详细部署
  - Nginx 配置
  - SSL 证书配置
  - 性能优化
  - 监控和日志

- **[版本更新记录](docs/CHANGELOG.md)** - 版本历史和更新内容

## 默认账号密码

首次部署需要创建管理员账户：

```bash
# 使用创建脚本
python create_admin.py
```

输入示例：
```
用户名: admin
邮箱: admin@example.com
密码: your_password
```

系统默认配置：
- **数据库用户**: `examuser`
- **数据库名称**: `examdb`
- **数据库密码**: 开发环境 `exam_password_123456` / 生产环境需自定义

⚠️ **生产环境必须修改所有默认密码！**

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
- **PostgreSQL** - 生产环境推荐
- **SQLite** - 开发环境

### AI 集成
- **DeepSeek API** - 智能解析支持
- **OpenAI API** - GPT 模型支持

### 缓存
- **Redis 7** - 会话缓存和任务队列

### Web 服务器
- **Gunicorn** - WSGI 服务器
- **Nginx 1.25** - 反向代理

## 项目结构

```
/在线答题系统v3/
├── app/                          # 主应用包
│   ├── __init__.py              # 应用工厂
│   ├── models/                  # 数据层 - SQLAlchemy 模型
│   │   ├── user.py             # 用户模型
│   │   ├── subject.py          # 科目模型
│   │   ├── question.py         # 题目模型
│   │   ├── exam.py             # 试卷模型
│   │   └── ...
│   ├── services/                # 服务层 - 业务逻辑封装
│   │   ├── exam_service.py     # 试卷服务
│   │   ├── grade_service.py    # 成绩服务
│   │   └── ...
│   ├── parsers/                 # 解析层 - 文档解析器
│   │   ├── docx_parser.py      # Word 解析器
│   │   ├── pdf_parser.py       # PDF 解析器
│   │   └── ai_parser.py        # AI 解析器
│   ├── utils/                   # 工具层 - 通用工具函数
│   │   ├── decorators.py       # 装饰器
│   │   ├── helpers.py          # 辅助函数
│   │   └── ...
│   ├── routes/                  # 视图层 - Flask 路由
│   │   ├── auth.py             # 认证路由
│   │   ├── student.py          # 学生路由
│   │   ├── teacher.py          # 教师路由
│   │   ├── admin.py            # 管理员路由
│   │   └── ...
│   ├── templates/               # 模板层 - Jinja2 模板
│   │   ├── auth/               # 认证模板
│   │   ├── student/            # 学生模板
│   │   ├── teacher/            # 教师模板
│   │   ├── admin/              # 管理员模板
│   │   └── partials/           # 局部模板
│   └── static/                  # 静态资源
│       ├── css/                # 样式文件
│       ├── js/                 # JavaScript 文件
│       └── img/                # 图片文件
├── tests/                       # 测试目录
├── migrations/                  # 数据库迁移文件
├── scripts/                     # 部署脚本
│   ├── deploy-production.sh   # 生产环境一键部署
│   ├── backup-db.sh          # 数据库备份脚本
│   └── ...
├── docker/                       # Docker 配置
│   ├── init-db.sql           # 数据库初始化脚本
│   ├── postgresql.conf      # PostgreSQL 配置
│   └── nginx/                # Nginx 配置
│       ├── nginx.conf       # Nginx 主配置
│       └── conf.d/           # 应用配置
├── docs/                        # 项目文档
│   ├── DEPLOYMENT_GUIDE.md   # 部署指南（推荐）
│   ├── PRODUCTION_DEPLOYMENT.md  # 生产环境部署
│   └── CHANGELOG.md          # 版本更新记录
├── config.py                   # 配置文件
├── run.py                      # 开发入口
├── wsgi.py                     # 生产入口
├── requirements.txt            # 生产依赖
├── requirements-dev.txt        # 开发依赖
├── Dockerfile                   # Docker 镜像文件
├── docker-compose.yml           # 开发环境配置
├── docker-compose.prod.yml      # 生产环境配置
└── create_admin.py             # 创建管理员脚本
```

## 开发指南

### 代码规范
- 单个函数不超过 50 行
- 所有函数必须有类型注解和文档字符串
- 使用 black 和 isort 自动格式化代码
- 提交前运行 mypy 进行类型检查
- 遵循 PEP 8 代码风格

### 代码格式化
```bash
# 格式化代码
black app/ tests/
isort app/ tests/

# 检查格式
black --check app/ tests/
isort --check-only app/ tests/
```

### 测试
```bash
# 运行所有测试
pytest

# 运行特定测试文件
pytest tests/test_models.py

# 生成测试覆盖率报告
pytest --cov=app --cov-report=html
```

### 数据库迁移
```bash
# 创建迁移文件
flask db migrate -m "描述变更内容"

# 应用迁移
flask db upgrade

# 回滚迁移
flask db downgrade
```

## 贡献指南

欢迎贡献代码！请遵循以下流程：

1. **Fork 项目**：点击右上角 Fork 按钮
2. **创建功能分支**：`git checkout -b feature/新功能`
3. **提交更改**：`git commit -m '添加新功能'`
4. **推送分支**：`git push origin feature/新功能`
5. **创建 Pull Request**：在 GitHub 上提交 PR

### 提交规范

提交消息格式：
```
feat: 添加新功能描述
fix: 修复某个问题
docs: 更新文档
style: 代码格式调整
refactor: 重构代码
test: 添加测试
chore: 构建过程或辅助工具的变动
```

### 代码审查

- 确保代码通过所有测试
- 运行 `black` 和 `isort` 格式化代码
- 运行 `mypy` 进行类型检查
- 更新相关文档

## 常见问题

### Q: 如何重置数据库？
```bash
# 删除数据库文件
rm instance/exam_system.db  # SQLite
# 或
psql -U postgres -c "DROP DATABASE examdb;"  # PostgreSQL

# 重新初始化
flask db upgrade
```

### Q: 如何创建管理员账号？
```bash
# 运行管理员创建脚本
python create_admin.py

# 默认账号信息：
# 用户名: admin
# 密码: admin
# 邮箱: admin@example.com
```

**注意：** 首次登录后请立即修改密码！

### Q: 如何配置 AI 解析？
AI 配置在管理员后台进行设置，无需修改 `.env` 文件：

1. 使用管理员账号登录系统
2. 进入"后台管理" -> "AI配置"
3. 配置 AI 提供商（DeepSeek / OpenAI）
4. 填写 API Key 和 Base URL
5. 保存配置即可使用

### Q: 如何修改上传文件大小限制？
上传文件大小限制在管理员后台进行设置，或者编辑 `.env` 文件：

1. 管理员后台：系统设置 -> 文件上传设置
2. 编辑 `.env` 文件（单位：字节）：
```
MAX_CONTENT_LENGTH=52428800  # 50MB
```

### Q: 如何查看日志？
```bash
# 开发环境日志
tail -f logs/exam_system.log

# 生产环境（systemd）
sudo journalctl -u exam-system -f

# Docker 日志
docker-compose logs -f web
```

### Q: 学生如何绑定教师？
1. 学生登录后进入个人中心
2. 在"绑定教师"页面输入教师 ID
3. 提交绑定申请
4. 教师在"绑定申请"中批准申请
5. 绑定成功后，学生可以查看教师发布的试卷

## 版本历史

### v1.1.0 (2026-03-04)
- ✨ 添加提交记录批量删除功能
- 🐛 修复提交记录页面分值和状态显示错误
- 🐛 修复密码修改功能，修改成功后自动登出
- 🎨 优化页脚设计和布局
- 🐛 移除管理员首页的最近提交记录
- ⚠️ **已知问题**：部分页面权限检查不完善，无需登录即可访问（待修复）

### v1.0.0 (2026-02-27) - 🎉 首个正式发布版本
- 完整的 Docker 部署支持
- 完善的部署文档和快速部署脚本
- 生产环境优化建议

- **v0.9.6** (2026-02-27)
  - 修复教师绑定申请功能
  - 完善学生绑定教师流程
  - 添加绑定申请状态管理

- **v0.9.5** (2026-02-26)
  - 添加教师注册和学生绑定功能
  - 优化用户权限管理

更多版本历史请查看 [CHANGELOG.md](docs/CHANGELOG.md)。

## 技术支持

- 📖 **文档**：查看 [部署文档](docs/DEPLOYMENT.md)
- 🐛 **问题反馈**：提交 GitHub Issue
- 💬 **讨论**：参与 GitHub Discussions
- 📧 **邮件**：联系技术支持团队

## 许可证

[MIT License](LICENSE)

## 致谢

感谢所有贡献者和开源项目的支持！