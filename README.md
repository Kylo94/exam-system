# 在线答题系统 - FastAPI重构版

基于 FastAPI + Tortoise-ORM + Jinja2 的在线答题系统。

## 技术栈

- **Web框架**: FastAPI 0.109+
- **ORM**: Tortoise-ORM (异步)
- **数据库**: SQLite (开发) / PostgreSQL (生产)
- **认证**: JWT + Passlib
- **前端**: Jinja2 模板 + Bootstrap 5

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env 文件，修改必要的配置
```

### 3. 初始化数据库

```bash
python run.py create-admin
```

### 4. 启动开发服务器

```bash
python run.py --reload
```

访问 http://localhost:8000

## Docker部署

### 开发环境

```bash
docker-compose up -d
```

访问 http://localhost:8000

### 生产环境

```bash
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

## 默认账户

- 用户名: `admin`
- 密码: `admin123`

## 项目结构

```
├── app/
│   ├── models/          # Tortoise-ORM 数据模型
│   ├── routers/         # FastAPI 路由
│   └── config.py        # 配置文件
├── templates/           # Jinja2 模板
├── static/              # 静态文件
├── uploads/             # 上传文件目录
├── main.py              # 应用入口
├── run.py               # 启动脚本
└── docker-compose.yml   # Docker配置
```

## API路由

| 路径 | 说明 |
|------|------|
| `/` | 首页 |
| `/auth/login` | 登录 |
| `/auth/register` | 注册 |
| `/dashboard` | 控制台 |
| `/admin/*` | 管理员路由 |
| `/teacher/*` | 教师路由 |
| `/student/*` | 学生路由 |
| `/api/*` | REST API |

## License

MIT
