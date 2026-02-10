# 在线答题系统 v3.0

基于Flask的模块化、可扩展的在线答题系统，支持Word文档上传、AI智能解析、多题型自动判卷。

## 功能特性

### 核心功能
- **用户系统**：学生答题、成绩查看
- **试卷管理**：科目/等级分类、试卷列表
- **试题解析**：Word文档上传、AI/传统双解析器、图片提取
- **答题判卷**：多题型支持（单选/多选/判断/填空/主观/编程）、自动判卷
- **后台管理**：科目/等级管理、成绩统计、题目编辑

### 技术特色
- **模块化架构**：清晰的分层设计（数据层、服务层、解析层、工具层、视图层、模板层）
- **类型安全**：完整的Python类型注解
- **代码规范**：单个函数不超过50行，高内聚低耦合
- **错误处理**：统一的异常处理机制
- **易于扩展**：插件式解析器、判卷器设计

## 技术栈

### 后端
- Python 3.9+
- Flask 3.0+ - Web框架
- SQLAlchemy 2.0+ - ORM
- Flask-Migrate - 数据库迁移
- python-docx - Word文档解析
- Pillow - 图片处理

### 前端
- Bootstrap 5.3 - CSS框架
- Jinja2 - 模板引擎
- Chart.js - 数据可视化

### AI集成
- langchain - 多AI提供商统一接口
- DeepSeek/OpenAI API支持

### 开发工具
- pytest - 单元测试
- black/isort - 代码格式化
- mypy - 类型检查
- python-dotenv - 环境变量管理

## 项目结构

```
/在线答题系统v3/
├── app/                           # 主应用包
│   ├── models/                   # 数据层 - SQLAlchemy模型
│   ├── services/                 # 服务层 - 业务逻辑封装
│   ├── parsers/                  # 解析层 - 文档解析器
│   ├── utils/                    # 工具层 - 通用工具函数
│   ├── routes/                   # 视图层 - Flask路由
│   ├── templates/                # 模板层 - Jinja2模板
│   └── static/                   # 静态资源
├── tests/                        # 测试目录
├── migrations/                   # 数据库迁移文件
└── docs/                         # 项目文档
```

## 快速开始

### 1. 环境配置
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
# 编辑 .env 文件，设置数据库和API密钥
```

### 2. 数据库初始化
```bash
# 初始化数据库
flask db init
flask db migrate -m "Initial migration"
flask db upgrade
```

### 3. 启动应用
```bash
# 开发模式
python run.py

# 或使用Flask CLI
flask run --host=0.0.0.0 --port=5002
```

### 4. 访问应用
- 前端界面：http://localhost:5002
- API文档：http://localhost:5002/api/docs

## 开发指南

### 代码规范
- 单个函数不超过50行
- 所有函数必须有类型注解和文档字符串
- 使用black和isort自动格式化代码
- 提交前运行mypy进行类型检查

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

### 生产环境配置
1. 使用PostgreSQL替换SQLite
2. 配置Gunicorn + Nginx
3. 设置环境变量
4. 启用HTTPS

### Docker部署
```bash
# 构建镜像
docker build -t exam-system:v3.0 .

# 运行容器
docker run -d -p 5002:5002 --env-file .env exam-system:v3.0
```

## 贡献指南

1. Fork项目
2. 创建功能分支 (`git checkout -b feature/新功能`)
3. 提交更改 (`git commit -m '添加新功能'`)
4. 推送到分支 (`git push origin feature/新功能`)
5. 创建Pull Request

## 许可证

MIT License