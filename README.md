# 在线答题系统

<div align="center">

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-green.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

基于 **FastAPI** + **Tortoise-ORM** 构建的智能在线答题平台，支持多种题型、AI批改和知识点管理。

[功能介绍](#功能特性) · [快速开始](#快速开始) · [项目结构](#项目结构) · [API文档](#api路由)

</div>

---

## 功能特性

### 三种角色权限

| 角色 | 功能范围 |
|------|----------|
| **管理员** | 用户管理、科目等级、知识点管理、试卷管理、AI配置、系统设置 |
| **教师** | 学生管理、试卷创建、批改管理、数据统计 |
| **学生** | 在线考试、专项练习、提交记录、绑定教师 |

### 核心功能

- **在线考试** — 计时作答、随机题目、自动评分
- **专项刷题** — 按知识点分类练习，错题回顾
- **AI 智能批改** — 选择题自动评分，简答题AI辅助评判
- **知识点体系** — 批量自动标签，题目与知识点多对多关联
- **试卷解析** — Word文档上传，AI自动解析提取题目
- **实时日志** — 系统运行全链路日志记录

---

## 快速开始

### 环境要求

- Python 3.10+
- SQLite (开发) / PostgreSQL (生产)

### 启动服务

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 初始化数据库（首次）
python scripts/seed_data.py

# 3. 启动服务
python main.py
# 或使用 uvicorn
uvicorn main:app --host 0.0.0.0 --port 8000
```

访问 **http://localhost:8000** 进入系统。

### 默认账户

| 角色 | 用户名 | 密码 |
|------|--------|------|
| 管理员 | admin | admin |
| 教师 | teacher1 | teacher123 |
| 学生 | student1 | student123 |

---

## 项目结构

```
答题网站/
├── app/
│   ├── models/              # 数据模型
│   │   ├── user.py          # 用户模型
│   │   ├── exam.py         # 试卷模型
│   │   ├── question.py      # 题目模型
│   │   ├── knowledge_point.py  # 知识点模型
│   │   ├── submission.py    # 提交记录模型
│   │   └── ai_config.py     # AI配置模型
│   ├── routers/             # API路由
│   │   ├── admin_views/     # 管理后台视图
│   │   ├── auth.py          # 认证路由
│   │   ├── student.py       # 学生路由
│   │   └── teacher.py       # 教师路由
│   ├── services/            # 业务逻辑层
│   ├── parsers/            # 文档解析器
│   ├── ai/                  # AI集成
│   └── config.py           # 配置文件
├── templates/              # Jinja2 模板
│   ├── admin/             # 管理后台
│   ├── student/           # 学生端
│   └── teacher/           # 教师端
├── logs/                   # 日志文件
├── data/                   # 数据库文件
└── main.py                 # 应用入口
```

---

## 技术栈

| 类别 | 技术 |
|------|------|
| Web 框架 | FastAPI 0.109+ |
| ORM | Tortoise-ORM (异步) |
| 数据库 | SQLite (开发) / PostgreSQL (生产) |
| 前端 | Jinja2 + Bootstrap 5 + Dark Theme |
| AI 集成 | OpenAI / DeepSeek / MiniMax |

---

## API路由

### 页面路由

| 路径 | 说明 |
|------|------|
| `/` | 首页 |
| `/auth/login` | 登录 |
| `/auth/register` | 注册 |
| `/dashboard` | 学生控制台 |
| `/admin` | 管理员控制台 |
| `/teacher` | 教师工作台 |

### 管理后台

| 路径 | 说明 |
|------|------|
| `/admin/users` | 用户管理 |
| `/admin/subjects` | 科目与等级 |
| `/admin/knowledge-points` | 知识点管理 |
| `/admin/exams` | 试卷管理 |
| `/admin/questions` | 题目管理 |
| `/admin/settings` | 系统设置（含日志查看） |

### REST API

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/subjects` | 获取科目列表 |
| GET | `/api/levels` | 获取难度等级 |
| GET | `/api/exams` | 获取试卷列表 |
| GET | `/api/knowledge-points` | 获取知识点列表 |
| POST | `/api/upload/parse/preview` | 解析试卷预览 |
| POST | `/api/upload/parse/save` | 保存解析结果 |

---

## License

MIT License
