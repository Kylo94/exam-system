# 在线答题系统

基于 FastAPI + Tortoise-ORM 构建的在线答题平台，支持管理员、教师、学生三种角色，提供在线考试、练习刷题、AI批改等功能。

## 技术栈

| 类别 | 技术 |
|------|------|
| Web 框架 | FastAPI 0.109+ |
| ORM | Tortoise-ORM (异步) |
| 数据库 | SQLite (开发) / PostgreSQL (生产) |
| 认证 | JWT + Passlib |
| 前端 | Jinja2 模板 + Bootstrap 5 |
| AI 集成 | OpenAI / DeepSeek / MiniMax API |

## 功能特性

### 角色权限

- **管理员**：用户管理、科目与等级管理、知识点管理、试卷管理、AI配置、绑定申请审批
- **教师**：学生管理、试卷管理、批改管理、数据统计
- **学生**：在线考试、专项刷题、提交记录、绑定教师

### 核心功能

- 在线考试系统（计时、随机题目）
- 专项刷题练习
- AI 智能批改（选择题、简答题）
- 知识点体系管理
- 试卷生成与管理
- 学生-教师绑定关系

## 项目结构

```
答题网站/
├── app/
│   ├── models/              # 数据模型
│   │   ├── user.py
│   │   ├── exam.py
│   │   ├── subject.py
│   │   ├── level.py
│   │   ├── knowledge_point.py
│   │   ├── question.py
│   │   ├── submission.py
│   │   └── ai_config.py
│   ├── routers/            # API 路由
│   │   ├── auth.py          # 认证
│   │   ├── admin.py        # 管理员
│   │   ├── teacher.py       # 教师
│   │   ├── student.py       # 学生
│   │   └── api.py          # REST API
│   ├── services/           # 业务逻辑
│   │   └── id_generator.py # ID生成器
│   ├── auth.py             # 认证模块
│   ├── config.py           # 配置
│   └── templating.py      # 模板配置
├── templates/              # Jinja2 模板
│   ├── admin/             # 管理员模板
│   ├── auth/              # 认证模板
│   ├── student/           # 学生模板
│   ├── teacher/           # 教师模板
│   └── *.html             # 共享模板
├── static/                 # 静态文件
├── scripts/               # 脚本
├── tests/                 # 测试
├── data/                  # 数据库文件
├── uploads/               # 上传文件
├── logs/                  # 日志
├── main.py                # 应用入口
├── requirements.txt       # 依赖
├── .env                   # 环境配置
├── Dockerfile
├── docker-compose.yml
└── nginx.conf
```

## 快速开始

### 环境要求

- Python 3.10+
- SQLite (开发环境自带)

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境

```bash
cp .env.example .env  # 复制配置模板
# 编辑 .env 文件修改配置（可选）
```

### 3. 初始化数据库

```bash
python scripts/seed_data.py
```

### 4. 启动服务

```bash
python main.py
# 或使用 uvicorn
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

访问 http://localhost:8000

## 默认账户

| 角色 | 用户名 | 密码 |
|------|--------|------|
| 管理员 | admin | admin123 |
| 教师 | teacher1 | teacher123 |
| 学生 | student1 | student123 |

## Docker 部署

### 开发环境

```bash
docker-compose up -d
```

### 生产环境

```bash
# 修改 .env 中的 SECRET_KEY 和 ADMIN_PASSWORD
docker-compose up -d --build
```

## API 路由

### 页面路由

| 路径 | 说明 |
|------|------|
| `/` | 首页 |
| `/auth/login` | 登录 |
| `/auth/register` | 注册 |
| `/auth/profile` | 个人资料 |
| `/dashboard` | 学生控制台 |
| `/admin` | 管理员控制台 |
| `/teacher` | 教师工作台 |
| `/student/exams` | 在线考试 |
| `/student/practice` | 专项刷题 |

### 管理后台

| 路径 | 说明 |
|------|------|
| `/admin/users` | 用户管理 |
| `/admin/subjects` | 科目与等级管理 |
| `/admin/knowledge-points` | 知识点管理 |
| `/admin/exams` | 试卷管理 |
| `/admin/bind-requests` | 绑定申请 |
| `/admin/ai-configs` | AI 配置 |

### REST API

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/subjects` | 获取科目列表 |
| GET | `/api/levels` | 获取难度等级列表 |
| GET | `/api/exams` | 获取试卷列表 |
| GET | `/api/knowledge-points` | 获取知识点列表 |
| GET | `/api/ai-configs` | 获取 AI 配置列表 |

## ID 分配规则

系统采用分段 ID，便于区分不同类型的实体：

| 类型 | 前缀 | 范围 |
|------|------|------|
| 管理员 | A | 1-999 |
| 教师 | T | 1001-1999 |
| 学生 | S | 2001-2999 |
| 试卷 | E | 3001-3999 |
| 科目 | C | 4001-4999 |
| 难度等级 | L | 5001-5999 |
| 知识点 | K | 6001-6999 |
| 题目 | Q | 7001-7999 |
| 提交记录 | B | 8001-8999 |
| AI 配置 | AI | 9001-9999 |

## License

MIT License
