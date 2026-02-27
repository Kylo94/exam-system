#!/bin/bash
# Docker 快速启动脚本

set -e

echo "=== Docker 部署启动脚本 ==="
echo ""

# 检查 Docker 和 Docker Compose
if ! command -v docker &> /dev/null; then
    echo "错误: 未检测到 Docker，请先安装 Docker"
    exit 1
fi

if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo "错误: 未检测到 Docker Compose，请先安装"
    exit 1
fi

# 确定使用 docker-compose 还是 docker compose
if docker compose version &> /dev/null; then
    DOCKER_COMPOSE="docker compose"
else
    DOCKER_COMPOSE="docker-compose"
fi

echo "检测到 Docker Compose: $DOCKER_COMPOSE"
echo ""

# 检查环境变量文件
if [ ! -f .env ]; then
    echo "创建 .env 文件..."
    cat > .env << EOF
FLASK_ENV=production
FLASK_PORT=5002
SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
DATABASE_URL=postgresql://examuser:exam_password_123456@db:5432/examdb
DB_PASSWORD=exam_password_123456
MAX_CONTENT_LENGTH=52428800
UPLOAD_FOLDER=uploads
DEEPSEEK_API_KEY=
OPENAI_API_KEY=
EOF
    echo ".env 文件已创建"
fi

# 创建必要的目录
echo "创建必要的目录..."
mkdir -p uploads logs nginx/ssl

# 构建镜像
echo "构建 Docker 镜像..."
$DOCKER_COMPOSE build

# 启动服务
echo "启动服务..."
$DOCKER_COMPOSE up -d

# 等待服务就绪
echo "等待服务启动..."
sleep 10

# 检查服务状态
echo ""
echo "=== 服务状态 ==="
$DOCKER_COMPOSE ps

# 初始化数据库
echo ""
echo "初始化数据库..."
$DOCKER_COMPOSE exec -T web flask db upgrade

# 创建管理员账号（如果不存在）
echo ""
echo "创建管理员账号..."
$DOCKER_COMPOSE exec -T web python create_admin.py

# 完成
echo ""
echo "=== 部署完成！==="
echo ""
echo "访问地址:"
echo "  - HTTP:  http://localhost:5002"
echo "  - HTTPS: https://localhost (需要配置 SSL 证书)"
echo ""
echo "管理命令:"
echo "  - 查看日志: $DOCKER_COMPOSE logs -f"
echo "  - 查看状态: $DOCKER_COMPOSE ps"
echo "  - 停止服务: $DOCKER_COMPOSE down"
echo "  - 重启服务: $DOCKER_COMPOSE restart"
echo "  - 进入容器: $DOCKER_COMPOSE exec web bash"
echo ""
