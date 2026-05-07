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
| **教师** | 学生管理、试卷授权、批改管理 |
| **学生** | 在线考试、专项练习、错题库、绑定教师 |

### 核心功能

- **在线考试** — 计时作答、自动保存进度、自动评分
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
├── main.py                 # FastAPI应用入口
├── requirements.txt         # 依赖配置
├── Dockerfile / docker-compose.yml  # 容器化配置
│
├── app/
│   ├── __init__.py         # 应用初始化
│   ├── config.py           # 配置管理（数据库、JWT密钥等）
│   ├── database.py         # Tortoise-ORM数据库初始化
│   ├── auth.py             # 认证模块（JWT+Passlib）
│   ├── tasks.py            # 异步任务管理
│   ├── templating.py       # Jinja2模板配置
│   ├── logging_config.py   # 日志配置
│   │
│   ├── routers/            # API路由层
│   │   ├── __init__.py
│   │   ├── main.py         # 主页路由 (/)
│   │   ├── auth.py         # 认证路由 (/auth/*)
│   │   ├── student.py      # 学生路由 (/student/*)
│   │   ├── teacher.py     # 教师路由 (/teacher/*)
│   │   ├── admin.py       # 管理员路由聚合
│   │   ├── admin_views/   # 管理员功能模块
│   │   │   ├── index.py   # 管理员首页/统计
│   │   │   ├── users.py   # 用户管理 (/admin/users)
│   │   │   ├── subjects.py # 科目/等级/知识点 (/admin/subjects)
│   │   │   ├── exams.py   # 试卷管理 (/admin/exams)
│   │   │   ├── questions.py # 题目管理 (/admin/questions)
│   │   │   ├── misc.py    # 系统设置/日志/审计(/admin/*)
│   │   │   └── __init__.py
│   │   └── api.py         # REST API (/api/*)
│   │
│   ├── services/           # 业务逻辑层
│   │   ├── base.py
│   │   ├── user_service.py      # 用户CRUD
│   │   ├── exam_service.py     # 试卷CRUD
│   │   ├── question_service.py # 题目CRUD
│   │   ├── subject_service.py  # 科目/等级/知识点管理
│   │   ├── exam_access_service.py # 学生试卷授权
│   │   ├── wrong_question_service.py # 错题记录
│   │   ├── knowledge_point_service.py # 知识点批量匹配
│   │   ├── id_generator.py
│   │   └── exceptions.py
│   │
│   ├── models/            # 数据模型层 (Tortoise-ORM)
│   │   ├── user.py        # 用户模型
│   │   ├── subject.py     # 科目模型
│   │   ├── level.py       # 等级模型
│   │   ├── exam.py        # 试卷模型
│   │   ├── question.py    # 题目模型
│   │   ├── submission.py  # 提交记录模型
│   │   ├── answer.py      # 答案模型
│   │   ├── knowledge_point.py  # 知识点模型
│   │   ├── teacher_bind_request.py # 师生绑定申请
│   │   ├── student_exam_access.py  # 学生试卷授权
│   │   ├── wrong_question.py     # 错题记录
│   │   ├── ai_config.py   # AI配置模型
│   │   ├── system_settings.py # 系统设置
│   │   ├── audit_log.py   # 审计日志
│   │   └── __init__.py
│   │
│   ├── parsers/           # 文档解析模块
│   │   ├── base.py       # 解析器基类
│   │   ├── factory.py    # 解析器工厂
│   │   ├── docx_extractor.py  # Word文档文本提取
│   │   ├── docx_parser.py    # Docx解析器
│   │   ├── text_parser.py    # 纯文本解析器
│   │   ├── rule_parser.py    # 规则解析器
│   │   ├── question_parser.py # 统一解析入口
│   │   ├── ai_parser.py     # AI增强解析
│   │   └── json_handler.py  # JSON标准化
│   │
│   ├── ai/               # AI服务模块
│   │   ├── base.py       # AI服务基类
│   │   ├── llm_service.py    # 大语言模型对话
│   │   ├── grader_service.py # AI批改服务
│   │   ├── generator_service.py # AI题目生成
│   │   └── providers/    # 多AI提供商
│   │       ├── deepseek.py
│   │       ├── deepseek_anthropic.py
│   │       ├── openai.py
│   │       └── minimax.py
│   │
│   └── utils/            # 工具模块
│       ├── file_utils.py
│       ├── image_utils.py
│       ├── question_utils.py
│       └── validators.py
│
├── templates/            # Jinja2模板
│   ├── base.html         # 基础模板
│   ├── index.html        # 首页
│   ├── admin/           # 管理后台模板
│   ├── auth/            # 认证模板
│   ├── exam/            # 考试模板
│   ├── student/         # 学生端模板
│   ├── teacher/         # 教师端模板
│   ├── submission/       # 提交记录模板
│   ├── question/         # 题目模板
│   ├── partials/        # 公共片段
│   └── errors/          # 错误页面
│
├── static/              # 静态文件
├── tests/               # 测试文件
├── scripts/              # 脚本
│   └── seed_data.py     # 数据初始化脚本
├── data/                 # 数据库文件
├── logs/                 # 日志文件
└── uploads/             # 上传文件
```

---

## 架构说明

### 三层架构

```
┌─────────────────────────────────────────┐
│  Router Layer (routers/)               │  路由层：接收请求、参数验证、调用服务
├─────────────────────────────────────────┤
│  Service Layer (services/)              │  服务层：业务逻辑、数据处理
├─────────────────────────────────────────┤
│  Model Layer (models/)                  │  模型层：数据模型、数据库操作
└─────────────────────────────────────────┘
```

### 核心调用链

1. **试卷解析流程**
   ```
   Word文件 → docx_extractor → question_parser → rule_parser/ai_parser → json_handler → Question模型
   ```

2. **答题流程**
   ```
   答题页面 → autosave保存 → submit提交 → 自动评分 → WrongQuestion记录 → 结果展示
   ```

3. **授权流程**
   ```
   教师创建绑定申请 → 学生申请 → 教师审批 → 授权试卷类型 → 学生可访问该类型试卷
   ```

---

## API路由

### 页面路由

| 路径 | 方法 | 说明 |
|------|------|------|
| `/` | GET | 首页 |
| `/auth/login` | GET/POST | 登录 |
| `/auth/register` | GET/POST | 注册 |
| `/auth/logout` | GET | 登出 |
| `/dashboard` | GET | 角色主页 |

### 学生端 `/student`

| 路径 | 方法 | 说明 |
|------|------|------|
| `/student/` | GET | 学生首页 |
| `/student/exams` | GET | 我的试卷列表 |
| `/student/exam/{id}/take` | GET | 答题页面 |
| `/student/exam/{id}/autosave` | POST | 自动保存 |
| `/student/exam/{id}/submit` | POST | 提交答案 |
| `/student/exam/{id}/result/{sid}` | GET | 答题结果 |
| `/student/history` | GET | 答题历史 |
| `/student/kp-practice` | GET | 知识点练习首页 |
| `/student/kp-practice/{sid}` | GET | 按科目选择知识点 |
| `/student/kp-practice/{sid}/kp/{kid}` | GET | 知识点练习 |
| `/student/wrong-questions` | GET | 错题库 |
| `/student/bind-teacher` | GET/POST | 绑定教师 |

### 教师端 `/teacher`

| 路径 | 方法 | 说明 |
|------|------|------|
| `/teacher/` | GET | 教师首页 |
| `/teacher/students` | GET | 我的学生 |
| `/teacher/exam-access` | GET | 授权管理 |
| `/teacher/exam-access/grant` | POST | 授予权限 |
| `/teacher/bind-requests` | GET | 绑定申请 |
| `/teacher/bind-requests/{id}/approve` | POST | 批准绑定 |
| `/teacher/bind-requests/{id}/reject` | POST | 拒绝绑定 |
| `/teacher/submissions` | GET | 答题记录 |
| `/teacher/submissions/{id}/grade` | GET/POST | 评分 |

### 管理端 `/admin`

| 路径 | 方法 | 说明 |
|------|------|------|
| `/admin` | GET | 管理首页 |
| `/admin/users` | GET | 用户管理 |
| `/admin/subjects` | GET | 科目/等级 |
| `/admin/exams` | GET | 试卷管理 |
| `/admin/exams/create` | GET/POST | 创建试卷 |
| `/admin/exams/{id}/edit` | GET/POST | 编辑试卷 |
| `/admin/questions` | GET | 题目管理 |
| `/admin/bind-requests` | GET | 绑定申请管理 |
| `/admin/submissions` | GET | 提交记录 |
| `/admin/ai-configs` | GET | AI配置 |
| `/admin/settings` | GET | 系统设置 |
| `/admin/audit-logs` | GET | 审计日志 |
| `/admin/statistics` | GET | 数据统计 |

### REST API `/api`

| 路径 | 方法 | 说明 |
|------|------|------|
| `/api/subjects` | GET/POST | 科目CRUD |
| `/api/subjects/{id}` | GET/PUT/DELETE | 科目操作 |
| `/api/levels` | GET | 等级列表 |
| `/api/knowledge-points` | GET/POST | 知识点CRUD |
| `/api/exams` | GET/POST | 试卷CRUD |
| `/api/exams/{id}` | GET/PUT/DELETE | 试卷操作 |
| `/api/exams/{id}/questions` | GET/POST | 题目列表/创建 |
| `/api/questions/{id}` | PUT/DELETE | 题目操作 |
| `/api/submissions` | GET | 提交记录列表 |
| `/api/users/me` | GET | 当前用户信息 |
| `/api/ai-configs` | GET/POST | AI配置CRUD |
| `/api/ai-configs/{id}/test` | POST | 测试AI配置 |
| `/api/health` | GET | 健康检查 |

---

## 数据模型

### 核心实体关系

```
User (用户)
├── role: admin/teacher/student
├── teacher_id: 绑定教师 (学生)
│
├── TeacherBindRequest (绑定申请)
│   ├── student_id → User
│   └── teacher_id → User
│
├── StudentExamAccess (试卷授权)
│   ├── student_id → User
│   ├── teacher_id → User (授权教师)
│   ├── subject_id → Subject
│   └── level_id → Level (可选)
│
└── Submission (答题记录)
    ├── user_id → User
    ├── exam_id → Exam
    │
    └── Answer (答案)
        ├── submission_id → Submission
        └── question_id → Question

Subject (科目)
└── Level (等级)
    └── KnowledgePoint (知识点)

Exam (试卷)
└── Question (题目)
    ├── knowledge_point_id → KnowledgePoint
    └── type: single_choice/multiple_choice/true_false/fill_blank/short_answer/coding
```

### 题目类型

| type值 | 说明 | 自动评分 |
|--------|------|----------|
| `single_choice` | 单选题 | ✅ |
| `multiple_choice` | 多选题 | ✅ |
| `true_false` | 判断题 | ✅ |
| `fill_blank` | 填空题 | ✅ |
| `short_answer` | 简答题 | AI辅助 |
| `coding` | 编程题 | 需教师批改 |

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

---

## License

MIT License
