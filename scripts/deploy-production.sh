#!/bin/bash

# ========================================
# 生产环境部署脚本
# ========================================

set -e  # 遇到错误立即退出

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 打印分隔线
print_separator() {
    echo "========================================"
}

# 检查 Docker 和 Docker Compose
check_dependencies() {
    log_info "检查依赖项..."

    if ! command -v docker &> /dev/null; then
        log_error "Docker 未安装，请先安装 Docker"
        exit 1
    fi

    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        log_error "Docker Compose 未安装，请先安装 Docker Compose"
        exit 1
    fi

    log_success "依赖项检查通过"
}

# 检查环境配置
check_environment() {
    log_info "检查环境配置..."

    if [ ! -f .env.production ]; then
        log_error ".env.production 文件不存在"
        log_info "复制示例配置文件..."
        cp .env.production.example .env.production 2>/dev/null || {
            log_warning ".env.production.example 不存在，创建默认配置"
            cat > .env.production << 'EOF'
FLASK_PORT=5002
NGINX_HTTP_PORT=80
NGINX_HTTPS_PORT=443
SECRET_KEY=please-change-this-secret-key-in-production
SECURITY_PASSWORD_SALT=please-change-this-salt
DB_PASSWORD=change-this-password
GUNICORN_WORKERS=4
GUNICORN_THREADS=2
LOG_LEVEL=INFO
EOF
        }
        log_warning "请编辑 .env.production 文件并修改相关配置"
        read -p "是否现在编辑配置文件？(y/n) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            ${EDITOR:-nano} .env.production
        fi
    fi

    # 检查关键配置是否已修改
    if grep -q "please-change-this" .env.production; then
        log_warning "检测到未修改的默认配置，建议修改以下项："
        grep "please-change-this" .env.production
        read -p "继续部署？(y/n) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 0
        fi
    fi

    log_success "环境配置检查通过"
}

# 创建必要的目录
create_directories() {
    log_info "创建必要的目录..."

    mkdir -p data/postgres
    mkdir -p data/redis
    mkdir -p data/uploads
    mkdir -p data/logs
    mkdir -p data/nginx
    mkdir -p uploads
    mkdir -p logs
    mkdir -p docker/nginx/ssl
    mkdir -p docker/nginx/conf.d

    # 设置目录权限
    chmod 755 data/postgres data/redis data/uploads data/logs data/nginx
    chmod 755 docker/nginx/ssl docker/nginx/conf.d

    log_success "目录创建完成"
}

# 拉取最新镜像
pull_images() {
    log_info "拉取最新 Docker 镜像..."
    docker-compose -f docker-compose.prod.yml pull
    log_success "镜像拉取完成"
}

# 构建应用镜像
build_image() {
    log_info "构建应用镜像..."
    docker-compose -f docker-compose.prod.yml build web
    log_success "镜像构建完成"
}

# 初始化数据库
init_database() {
    log_info "初始化数据库..."

    # 等待数据库就绪
    log_info "等待数据库启动..."
    docker-compose -f docker-compose.prod.yml up -d db

    max_attempts=30
    attempt=0
    while [ $attempt -lt $max_attempts ]; do
        if docker-compose -f docker-compose.prod.yml exec -T db pg_isready -U examuser -d examdb &>/dev/null; then
            log_success "数据库已就绪"
            break
        fi
        attempt=$((attempt + 1))
        echo -n "."
        sleep 2
    done

    if [ $attempt -eq $max_attempts ]; then
        log_error "数据库启动超时"
        exit 1
    fi

    # 运行数据库迁移
    log_info "运行数据库迁移..."
    docker-compose -f docker-compose.prod.yml run --rm web flask db upgrade

    # 创建管理员账号（如果不存在）
    log_info "检查管理员账号..."
    docker-compose -f docker-compose.prod.yml run --rm web python -c "
from app import create_app, db
from app.models.user import User
import sys

app = create_app()
with app.app_context():
    admin = User.query.filter_by(username='admin').first()
    if not admin:
        try:
            admin = User(
                username='admin',
                email='admin@example.com',
                password='admin',
                role='admin',
                is_active=True
            )
            db.session.add(admin)
            db.session.commit()
            print('管理员账号创建成功')
            print('用户名: admin')
            print('密码: admin')
            print('邮箱: admin@example.com')
            print('⚠️  请立即登录并修改密码！')
        except Exception as e:
            print(f'创建管理员失败: {e}', file=sys.stderr)
            sys.exit(1)
    else:
        print('管理员账号已存在')
"

    log_success "数据库初始化完成"
}

# 启动所有服务
start_services() {
    log_info "启动所有服务..."

    # 使用生产环境配置
    export $(cat .env.production | xargs)

    docker-compose -f docker-compose.prod.yml up -d

    log_success "服务启动完成"
}

# 检查服务状态
check_services() {
    log_info "检查服务状态..."

    sleep 5

    docker-compose -f docker-compose.prod.yml ps

    log_info "等待所有服务就绪..."
    sleep 10

    # 检查健康状态
    if docker-compose -f docker-compose.prod.yml ps | grep -q "unhealthy"; then
        log_warning "部分服务状态异常，请检查日志"
        log_info "查看日志: docker-compose -f docker-compose.prod.yml logs -f"
    else
        log_success "所有服务运行正常"
    fi
}

# 显示访问信息
show_access_info() {
    print_separator
    log_success "部署完成！"
    print_separator
    echo
    echo "访问地址:"
    echo "  HTTP:  http://localhost:80"
    echo "  HTTPS: https://localhost:443 (需配置 SSL 证书)"
    echo
    echo "管理员账号 (首次部署):"
    echo "  用户名: admin"
    echo "  密码: admin"
    echo "  ⚠️  请立即登录并修改密码！"
    echo
    echo "常用命令:"
    echo "  查看日志: docker-compose -f docker-compose.prod.yml logs -f"
    echo "  查看状态: docker-compose -f docker-compose.prod.yml ps"
    echo "  停止服务: docker-compose -f docker-compose.prod.yml down"
    echo "  重启服务: docker-compose -f docker-compose.prod.yml restart"
    echo
    echo "数据库管理:"
    echo "  进入数据库: docker-compose -f docker-compose.prod.yml exec db psql -U examuser -d examdb"
    echo "  备份数据: ./scripts/backup-db.sh"
    echo
    print_separator
}

# 主函数
main() {
    print_separator
    log_info "开始生产环境部署"
    print_separator
    echo

    check_dependencies
    echo
    check_environment
    echo
    create_directories
    echo
    pull_images
    echo
    build_image
    echo
    init_database
    echo
    start_services
    echo
    check_services
    echo
    show_access_info
}

# 执行主函数
main
