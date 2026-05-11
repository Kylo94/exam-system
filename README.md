# 在线答题系统 v0.9.0

<div align="center">

![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-green.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

基于 **FastAPI** + **Tortoise-ORM** + **Jinja2** 构建的智能在线答题平台，支持多种题型、AI批改和知识点驱动练习。

[功能介绍](#功能特性) · [快速开始](#快速开始) · [Docker部署](#docker部署) · [项目结构](#项目结构)

</div>

---

## 功能特性

### 三种角色权限

| 角色 | 功能范围 |
|------|----------|
| **管理员** | 用户管理、科目等级、知识点管理、试卷管理、题目管理、AI配置、系统设置、审计日志 |
| **教师** | 学生管理、绑定申请审批、试卷授权、答题记录批改 |
| **学生** | 在线考试、专项练习（按知识点）、错题库、错题练习、绑定教师 |

### 核心功能

- **在线考试** — 计时作答、自动保存进度、自动评分
- **专项刷题** — 按知识点分类练习，tags智能匹配题目
- **错题本** — 自动记录答题错误，薄弱点强化练习
- **AI标签生成** — 批量为题目生成高质量标签，自动过滤垃圾标签
- **AI智能分配知识点** — 根据题目标签自动归类到对应知识点
- **AI合并相似知识点** — 智能识别并合并高度相似的知识点
- **服务器图片浏览器** — 编辑题目时可直接选择服务器已有图片
- **试卷解析** — Word文档上传，AI自动解析提取多种题型题目
- **实时进度反馈** — SSE流式输出AI处理进度

---

## 快速开始

### 环境要求

- Python 3.10+ 或 Docker
- SQLite (开发) / PostgreSQL (生产)

### 本地开发

```bash
# 1. 克隆代码
git clone <repo-url>
cd 答题网站

# 2. 安装依赖
pip install -r requirements.txt

# 3. 初始化数据库
python scripts/seed_data.py

# 4. 启动服务
python main.py
# 或使用 uvicorn
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

访问 **http://localhost:8000** 进入系统。

### 默认账户

| 角色 | 用户名 | 密码 |
|------|--------|------|
| 管理员 | admin | admin |
| 教师 | teacher1 | teacher123 |
| 学生 | student1 | student123 |

---

## Docker部署

### 方式一：docker-compose（推荐）

```bash
# 启动所有服务（app + postgres + nginx）
docker-compose --profile with-nginx up -d

# 仅启动核心服务（app + postgres）
docker-compose up -d
```

访问 **http://localhost:8000**（或 http://localhost 如果启用nginx）

### 方式二：Dockerfile

```bash
# 构建镜像
docker build -t exam-system .

# 运行容器
docker run -d \
  --name exam_system \
  -p 8000:8000 \
  -e DATABASE_URL=sqlite:///data/exam_system.db \
  -v ./data:/app/data \
  -v ./uploads:/app/uploads \
  exam-system
```

### 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `DATABASE_URL` | 数据库连接URL | `sqlite:///data/exam_system.db` |
| `SECRET_KEY` | JWT密钥 | `dev-secret-key-change-in-production` |
| `DEBUG` | 调试模式 | `false` |
| `LOG_LEVEL` | 日志级别 | `DEBUG` |
| `ADMIN_USERNAME` | 管理员用户名 | `admin` |
| `ADMIN_PASSWORD` | 管理员密码 | `admin` |

---

## 项目结构

```
答题网站/
├── main.py                    # FastAPI应用入口
├── requirements.txt           # 依赖配置
├── Dockerfile                 # Docker镜像构建
├── docker-compose.yml         # 容器编排
├── nginx.conf                 # Nginx配置
│
├── app/
│   ├── __init__.py
│   ├── config.py              # 配置管理
│   ├── database.py            # Tortoise-ORM数据库初始化
│   ├── auth.py                # 认证模块（JWT）
│   ├── config.py              # 配置管理
│   ├── logging_config.py      # 日志配置
│   ├── templating.py          # Jinja2模板配置
│   ├── tasks.py               # 异步任务管理
│   │
│   ├── routers/               # API路由层
│   │   ├── main.py            # 主页
│   │   ├── auth.py            # 认证 (/auth/*)
│   │   ├── student.py         # 学生 (/student/*)
│   │   ├── teacher.py         # 教师 (/teacher/*)
│   │   ├── api.py             # REST API (/api/*)
│   │   ├── upload.py          # 文件上传 (/admin/upload/*)
│   │   └── admin_views/       # 管理员功能模块
│   │       ├── index.py       # 管理首页/统计
│   │       ├── users.py       # 用户管理
│   │       ├── subjects.py    # 科目/等级/知识点
│   │       ├── exams.py       # 试卷管理
│   │       ├── questions.py   # 题目管理
│   │       └── misc.py        # 系统设置/日志/审计
│   │
│   ├── services/              # 业务逻辑层
│   │   ├── exam_service.py          # 试卷CRUD
│   │   ├── question_service.py      # 题目CRUD
│   │   ├── subject_service.py       # 科目/等级/知识点管理
│   │   ├── knowledge_point_service.py # 知识点AI匹配/合并
│   │   ├── parsing_service.py       # 文档解析服务
│   │   ├── upload_service.py        # 上传文件管理
│   │   ├── exam_access_service.py   # 学生试卷授权
│   │   └── wrong_question_service.py # 错题记录
│   │
│   ├── models/                # 数据模型层
│   │   ├── user.py            # 用户模型
│   │   ├── subject.py         # 科目模型
│   │   ├── level.py           # 等级模型
│   │   ├── knowledge_point.py # 知识点模型（含tags）
│   │   ├── exam.py            # 试卷模型
│   │   ├── question.py        # 题目模型（含tags）
│   │   ├── submission.py       # 提交记录模型
│   │   ├── answer.py          # 答案模型
│   │   └── ...
│   │
│   ├── parsers/               # 文档解析模块
│   │   ├── constants.py       # 公共常量
│   │   ├── docx_extractor.py  # Word文档文本提取
│   │   ├── ai_parser.py       # AI增强解析
│   │   ├── json_handler.py    # JSON标准化
│   │   └── ...
│   │
│   └── ai/                    # AI服务模块
│       ├── llm_service.py     # 大语言模型对话
│       └── providers/         # 多AI提供商
│
├── templates/                  # Jinja2模板
│   ├── base.html
│   ├── admin/                  # 管理后台
│   ├── student/               # 学生端
│   └── teacher/                # 教师端
│
├── static/                     # 静态文件
├── scripts/
│   └── seed_data.py            # 数据初始化
├── migrations/                 # 数据库迁移
├── data/                       # 数据库文件
├── logs/                       # 日志文件
└── uploads/                    # 上传文件
```

---

## 主要升级说明 (v0.9.0)

### 知识点驱动练习
- 题目新增 `tags` 字段，支持多标签
- 知识点新增 `tags` 字段，支持与题目标签智能匹配
- 题目可关联多个知识点（`knowledge_point_ids`）

### AI标签功能
- AI批量重构题目标签，过滤垃圾标签（运算符、关键字、文件后缀等）
- AI根据标签自动生成知识点
- AI合并相似知识点

### 服务器图片浏览器
- 题目编辑时可选择服务器已有图片
- 支持图片搜索和分页浏览
- 支持直接上传新图片

### 其他改进
- 修复答题结果页重复答案问题
- 修复错题练习属性错误问题
- 优化N+1查询性能
- 提取公共常量和SSE进度消息

---

## 技术栈

| 类别 | 技术 |
|------|------|
| Web 框架 | FastAPI 0.109+ |
| ORM | Tortoise-ORM (异步) |
| 数据库 | SQLite (开发) / PostgreSQL (生产) |
| 前端 | Jinja2 + Bootstrap 5 + Dark Theme |
| AI 集成 | OpenAI / DeepSeek / MiniMax |
| 认证 | JWT (python-jose) + Passlib |
| 容器化 | Docker + docker-compose |

---

## License

MIT License