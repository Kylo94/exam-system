# 在线答题系统 v3.0

基于 Flask 的模块化、可扩展的在线答题系统，支持 Word 文档上传、AI 智能解析、多题型自动判卷。

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

## 技术栈

### 后端
- **Python 3.9+** - 核心语言
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
- **SQLite** - 开发环境默认数据库
- **PostgreSQL** - 生产环境推荐数据库

### AI 集成
- **langchain** - 多 AI 提供商统一接口
- **DeepSeek API** - 智能解析支持
- **OpenAI API** - GPT 模型支持

### 缓存
- **Redis** - 会话缓存和任务队列（可选）

### Web 服务器
- **Gunicorn** - WSGI 服务器（生产环境）
- **Nginx** - 反向代理和静态文件服务

### 开发工具
- **pytest** - 单元测试
- **black/isort** - 代码格式化
- **mypy** - 类型检查
- **python-dotenv** - 环境变量管理

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
│   ├── deploy-linux.sh        # Linux 部署脚本
│   ├── deploy-windows.bat     # Windows 部署脚本
│   ├── docker-start.sh        # Docker 启动脚本
│   └── docker-start.bat       # Windows Docker 脚本
├── nginx/                       # Nginx 配置
│   └── nginx.conf             # Nginx 配置文件
├── docs/                        # 项目文档
│   └── DEPLOYMENT.md          # 部署文档
├── config.py                   # 配置文件
├── run.py                      # 开发入口
├── wsgi.py                     # 生产入口
├── requirements.txt            # 生产依赖
├── requirements-dev.txt        # 开发依赖
├── Dockerfile                   # Docker 镜像文件
├── docker-compose.yml           # Docker Compose 配置
└── create_admin.py             # 创建管理员脚本
```

## 快速开始

### 方式一：Docker 部署（推荐，最简单）

```bash
# 克隆项目
git clone <repository-url>
cd 答题网站

# 使用快速启动脚本（Linux/Mac）
./scripts/docker-start.sh

# Windows 使用
scripts\docker-start.bat

# 或手动启动
docker-compose up -d
```

### 方式二：本地开发环境

#### 1. 环境配置
```bash
# 克隆项目
git clone <repository-url>
cd 答题网站

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或 venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt
pip install -r requirements-dev.txt  # 开发环境

# 配置环境变量
cp .env.example .env
# 编辑 .env 文件，设置数据库和 API 密钥
```

#### 2. 数据库初始化
```bash
# 初始化数据库（首次部署）
flask db init
flask db migrate -m "Initial migration"
flask db upgrade

# 创建管理员账号
python create_admin.py
```

#### 3. 启动应用
```bash
# 开发模式
python run.py

# 或使用 Flask CLI
flask run --host=0.0.0.0 --port=5002
```

#### 4. 访问应用
- 前端界面：http://localhost:5002
- 默认管理员：首次运行 `create_admin.py` 时创建

### 方式三：Linux 生产环境

```bash
# 使用快速部署脚本（Ubuntu/Debian/CentOS）
./scripts/deploy-linux.sh
```

脚本会自动安装依赖、配置数据库、Nginx 并启动服务。

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

## 部署

详细的部署指南请查看 [部署文档](docs/DEPLOYMENT.md)，支持以下部署方式：

### 快速部署

#### Docker 部署（推荐）
```bash
# 使用快速启动脚本
./scripts/docker-start.sh

# 或手动启动
docker-compose up -d
```

**Docker 部署优势：**
- 一键部署，包含 PostgreSQL、Redis、Nginx
- 环境隔离，避免依赖冲突
- 易于迁移和扩展
- 自动健康检查和自动重启

#### Linux 部署
```bash
# 使用快速部署脚本（Ubuntu/Debian/CentOS）
./scripts/deploy-linux.sh
```

**Linux 部署优势：**
- 性能最优，适合生产环境
- 使用 Gunicorn + Nginx
- 完整的系统级监控和日志
- 支持自动备份和故障恢复

#### Windows 部署
```bash
# 使用快速部署脚本
scripts\deploy-windows.bat
```

**Windows 支持的方式：**
- WSL2（推荐 Linux 子系统）
- IIS + FastCGI
- Windows 服务（NSSM）
- Docker Desktop

### 生产环境配置

生产环境需要特别注意以下配置：

1. **数据库**：使用 PostgreSQL 替代 SQLite
2. **密钥安全**：设置强密码和 SECRET_KEY
3. **HTTPS**：配置 SSL/TLS 证书
4. **文件权限**：正确的目录和文件权限
5. **日志轮转**：配置日志自动清理
6. **自动备份**：定期备份数据库和文件
7. **监控告警**：配置系统监控

详细配置和故障排查请参考 [部署文档](docs/DEPLOYMENT.md)。

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

### Q: 如何修改上传文件大小限制？
编辑 `.env` 文件中的 `MAX_CONTENT_LENGTH`（单位：字节）：
```
MAX_CONTENT_LENGTH=52428800  # 50MB
```

### Q: 如何配置 AI 解析？
在 `.env` 文件中配置 API 密钥：
```
DEEPSEEK_API_KEY=your-deepseek-api-key
DEEPSEEK_BASE_URL=https://api.deepseek.com
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

## 版本历史

- **v0.9.6** (2026-02-27)
  - 修复教师绑定申请功能
  - 完善学生绑定教师流程
  - 添加绑定申请状态管理

- **v0.9.5** (2026-02-26)
  - 添加教师注册和学生绑定功能
  - 优化用户权限管理

更多版本历史请查看 [CHANGELOG.md](docs/CHANGELOG.md)（待创建）。

## 技术支持

- 📖 **文档**：查看 [部署文档](docs/DEPLOYMENT.md)
- 🐛 **问题反馈**：提交 GitHub Issue
- 💬 **讨论**：参与 GitHub Discussions
- 📧 **邮件**：联系技术支持团队

## 许可证

[MIT License](LICENSE)

## 致谢

感谢所有贡献者和开源项目的支持！