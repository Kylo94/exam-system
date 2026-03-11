# 生产环境测试说明

## 概述

生产环境已成功配置并测试通过！

## 当前配置

### 生产环境配置文件
- 配置文件：`.env.production`
- 运行端口：5002
- 数据库：SQLite (`instance/exam_prod.db`)
- WSGI服务器：Waitress (Windows/macOS 兼容)
- 日志级别：INFO

### 与开发环境的区别

| 配置项 | 开发环境 | 生产环境 |
|--------|---------|---------|
| 端口 | 5002 | 5002 |
| DEBUG | True | False |
| WSGI服务器 | Flask开发服务器 | Waitress |
| 数据库 | instance/exam.db | instance/exam_prod.db |
| 日志级别 | DEBUG | INFO |

## 快速启动

### 方法1：使用启动脚本（推荐）

```bash
./start_prod_simple.sh
```

### 方法2：手动启动

```bash
# 1. 加载配置并启动
python test_waitress.py &
```

### 方法3：使用 Waitress 命令行

```bash
waitress-serve --port=5002 --threads=4 wsgi:app
```

## 管理员账户

- 用户名：`admin`
- 密码：`admin`
- 邮箱：`admin@example.com`
- ⚠️ **请首次登录后立即修改密码！**

## 访问地址

- 主页：http://127.0.0.1:5002
- 登录页：http://127.0.0.1:5002/auth/login
- API基础：http://127.0.0.1:5002/api/

## 常用命令

### 查看服务状态
```bash
lsof -i:5002
```

### 停止服务
```bash
pkill -f 'python.*waitress'
```

### 查看日志
```bash
tail -f logs/exam_system.log
```

### 重启服务
```bash
pkill -f 'python.*waitress'
python test_waitress.py &
```

## 数据库管理

### 初始化数据库
```bash
python -c "
import os
from dotenv import load_dotenv
load_dotenv('.env.production')
from app import create_app
from app.extensions import db
app = create_app('production')
with app.app_context():
    db.create_all()
"
```

### 重置管理员账户
```bash
python create_admin.py
```
（确保设置了 `FLASK_ENV=production`）

## 性能优化建议

### Waitress 配置优化

当前配置（test_waitress.py）：
- `threads=4`：线程数
- `channel_timeout=120`：通道超时时间

可以根据服务器性能调整：
- CPU核心数较多：增加 threads
- 内存有限：减少 threads
- 长时间任务：增加 channel_timeout

### 生产环境推荐配置

如果要使用 PostgreSQL：

1. 修改 `.env.production` 中的数据库配置：
```
DATABASE_URL=postgresql://examuser:exam_password_123456@localhost:5432/examdb
```

2. 启动 PostgreSQL 服务

3. 使用 Flask-Migrate 进行数据库迁移

## 监控和日志

### 日志位置
- 应用日志：`logs/exam_system.log`
- 访问日志：`logs/access.log`
- 错误日志：`logs/error.log`

### 监控指标
- CPU 使用率
- 内存使用情况
- 请求数和响应时间
- 错误率

## 安全检查清单

- [x] DEBUG 模式已关闭
- [x] 生产环境数据库已配置
- [x] 管理员密码已设置（需要修改）
- [x] 日志级别设置为 INFO
- [ ] SECRET_KEY 需要修改为强密钥
- [ ] HTTPS 证书配置（如需）
- [ ] 防火墙规则配置
- [ ] 定期备份策略

## 故障排查

### 服务无法启动
1. 检查端口是否被占用：`lsof -i:5002`
2. 检查日志文件：`tail -50 logs/error.log`
3. 检查配置文件：`.env.production`

### 数据库连接错误
1. 确认数据库文件存在：`ls instance/exam_prod.db`
2. 检查数据库权限
3. 使用 PostgreSQL 时确认服务运行状态

### API 返回 500 错误
1. 查看错误日志
2. 确认数据库表已创建
3. 检查应用日志

## 测试验证

### 功能测试清单

- [x] 主页可访问
- [x] 登录页面正常
- [x] API 端点响应正常
- [x] 数据库连接正常
- [x] 管理员账户可登录
- [ ] 文件上传功能
- [ ] AI 评分功能
- [ ] 数据导出功能

### 性能测试建议

```bash
# 使用 Apache Bench 进行简单的压力测试
ab -n 1000 -c 10 http://127.0.0.1:5002/
```

## 部署到生产服务器

### Docker 部署（推荐用于生产环境）

项目已包含 Docker 配置文件：
- `Dockerfile`
- `docker-compose.yml`
- `docker-compose.prod.yml`

使用生产环境 Docker 部署：
```bash
./scripts/deploy-production.sh
```

### 直接部署到服务器

1. 安装依赖：`pip install -r requirements.txt`
2. 配置环境变量：编辑 `.env.production`
3. 初始化数据库：运行数据库迁移脚本
4. 启动服务：`./start_prod_simple.sh`
5. 配置反向代理（Nginx/Apache）
6. 配置 HTTPS

## 联系和支持

如有问题，请查看项目文档或联系开发团队。
