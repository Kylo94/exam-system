#!/bin/bash
# 快速部署脚本 - Linux

set -e

echo "=== 在线答题系统快速部署脚本 ==="
echo ""

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 检查是否为 root
if [ "$EUID" -eq 0 ]; then 
    echo -e "${RED}请不要使用 root 用户运行此脚本${NC}"
    exit 1
fi

# 检测操作系统
if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS=$ID
else
    echo -e "${RED}无法检测操作系统${NC}"
    exit 1
fi

echo -e "${GREEN}检测到操作系统: $OS${NC}"
echo ""

# 安装系统依赖
echo "=== 安装系统依赖 ==="
case $OS in
    ubuntu|debian)
        sudo apt update
        sudo apt install -y python3.11 python3-pip python3-venv postgresql postgresql-contrib nginx gcc libpq-dev curl
        ;;
    centos|rhel|fedora)
        sudo yum install -y python3.11 python3-pip postgresql-server nginx gcc postgresql-devel curl
        ;;
    *)
        echo -e "${RED}不支持的操作系统: $OS${NC}"
        exit 1
        ;;
esac

# 安装 Gunicorn
echo -e "${GREEN}安装 Gunicorn...${NC}"
sudo pip3 install gunicorn

# 创建项目目录
PROJECT_DIR="/opt/exam-system"
echo -e "${GREEN}创建项目目录: $PROJECT_DIR${NC}"
sudo mkdir -p $PROJECT_DIR
sudo chown $USER:$USER $PROJECT_DIR
cd $PROJECT_DIR

# 创建虚拟环境
echo -e "${GREEN}创建虚拟环境...${NC}"
python3 -m venv venv
source venv/bin/activate

# 安装 Python 依赖
echo -e "${GREEN}安装 Python 依赖...${NC}"
pip install --upgrade pip
pip install -r requirements.txt

# 配置数据库
echo -e "${GREEN}配置数据库...${NC}"
read -p "请输入数据库名称 (默认: examdb): " DB_NAME
DB_NAME=${DB_NAME:-examdb}

read -p "请输入数据库用户名 (默认: examuser): " DB_USER
DB_USER=${DB_USER:-examuser}

read -sp "请输入数据库密码: " DB_PASSWORD
echo
read -sp "确认数据库密码: " DB_PASSWORD_CONFIRM
echo

if [ "$DB_PASSWORD" != "$DB_PASSWORD_CONFIRM" ]; then
    echo -e "${RED}密码不匹配${NC}"
    exit 1
fi

# 创建数据库和用户
echo -e "${GREEN}创建 PostgreSQL 数据库和用户...${NC}"
sudo -u postgres psql << EOF
CREATE DATABASE $DB_NAME;
CREATE USER $DB_USER WITH ENCRYPTED PASSWORD '$DB_PASSWORD';
GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;
\q
EOF

# 配置环境变量
echo -e "${GREEN}配置环境变量...${NC}"
SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")

cat > .env << EOF
FLASK_ENV=production
FLASK_HOST=0.0.0.0
FLASK_PORT=5002
SECRET_KEY=$SECRET_KEY
DATABASE_URL=postgresql://$DB_USER:$DB_PASSWORD@localhost/$DB_NAME
MAX_CONTENT_LENGTH=52428800
UPLOAD_FOLDER=uploads
DEEPSEEK_API_KEY=
OPENAI_API_KEY=
EOF

# 初始化数据库
echo -e "${GREEN}初始化数据库...${NC}"
export FLASK_APP=run.py
flask db upgrade

# 创建管理员账号
echo -e "${GREEN}创建管理员账号...${NC}"
python create_admin.py

# 创建日志目录
sudo mkdir -p /var/log/exam-system
sudo chown www-data:www-data /var/log/exam-system

# 配置 systemd 服务
echo -e "${GREEN}配置 systemd 服务...${NC}"
sudo tee /etc/systemd/system/exam-system.service > /dev/null << EOF
[Unit]
Description=在线答题系统 Gunicorn 服务
After=network.target postgresql.service

[Service]
Type=notify
User=www-data
Group=www-data
RuntimeDirectory=exam-system
WorkingDirectory=$PROJECT_DIR
Environment="PATH=$PROJECT_DIR/venv/bin"
Environment="FLASK_ENV=production"
ExecStart=$PROJECT_DIR/venv/bin/gunicorn \
    --bind 127.0.0.1:5002 \
    --workers 4 \
    --threads 2 \
    --worker-class gthread \
    --timeout 120 \
    --access-logfile /var/log/exam-system/access.log \
    --error-logfile /var/log/exam-system/error.log \
    --log-level info \
    wsgi:app
ExecReload=/bin/kill -s HUP \$MAINPID
KillMode=mixed
TimeoutStopSec=5
PrivateTmp=true
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# 设置文件权限
sudo chown -R www-data:www-data $PROJECT_DIR

# 重载并启动服务
sudo systemctl daemon-reload
sudo systemctl start exam-system
sudo systemctl enable exam-system

# 配置 Nginx
echo -e "${GREEN}配置 Nginx...${NC}"
sudo tee /etc/nginx/sites-available/exam-system > /dev/null << EOF
upstream exam_backend {
    server 127.0.0.1:5002;
    keepalive 32;
}

server {
    listen 80;
    server_name _;

    client_max_body_size 20M;

    access_log /var/log/nginx/exam-access.log;
    error_log /var/log/nginx/exam-error.log;

    location /static/ {
        proxy_pass http://exam_backend;
        expires 30d;
        add_header Cache-Control "public, immutable";
        access_log off;
    }

    location /uploads/ {
        proxy_pass http://exam_backend;
        expires 30d;
        access_log off;
    }

    location / {
        proxy_pass http://exam_backend;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 120s;
    }
}
EOF

sudo ln -sf /etc/nginx/sites-available/exam-system /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl restart nginx

# 防火墙配置
echo -e "${GREEN}配置防火墙...${NC}"
if command -v ufw &> /dev/null; then
    sudo ufw allow 80/tcp
    sudo ufw allow 443/tcp
    sudo ufw --force enable
fi

# 完成提示
echo ""
echo -e "${GREEN}=== 部署完成！${NC}"
echo ""
echo "应用信息:"
echo "  - 访问地址: http://$(hostname -I | awk '{print $1}')"
echo "  - 应用目录: $PROJECT_DIR"
echo "  - 日志目录: /var/log/exam-system"
echo ""
echo "管理命令:"
echo "  - 查看状态: sudo systemctl status exam-system"
echo "  - 重启服务: sudo systemctl restart exam-system"
echo "  - 查看日志: sudo journalctl -u exam-system -f"
echo "  - Nginx 配置: sudo nginx -t && sudo systemctl reload nginx"
echo ""
echo -e "${YELLOW}下一步:${NC}"
echo "  1. 配置 SSL 证书: sudo certbot --nginx"
echo "  2. 修改 Nginx 配置中的 server_name"
echo "  3. 配置 AI API 密钥 (可选)"
echo ""
