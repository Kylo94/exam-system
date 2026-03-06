#!/bin/bash
# 生产环境启动脚本（简化版）

set -e

echo "========================================"
echo "生产环境启动脚本"
echo "========================================"
echo ""

# 检查依赖
if ! command -v python &> /dev/null; then
    echo "❌ Python 未安装"
    exit 1
fi

# 检查 waitress
if ! python -c "import waitress" 2>/dev/null; then
    echo "⚠️  Waitress 未安装，正在安装..."
    pip install waitress
fi

# 创建必要目录
echo "📁 创建必要目录..."
mkdir -p logs uploads

# 检查数据库
echo "🗄️  检查数据库..."
if [ ! -f "instance/exam_prod.db" ]; then
    echo "正在初始化数据库..."
    python -c "
import os
from dotenv import load_dotenv
load_dotenv('.env.production')
from app import create_app
from app.extensions import db
app = create_app('production')
with app.app_context():
    db.create_all()
    print('数据库初始化完成')
"
fi

# 检查管理员账户
echo "👤 检查管理员账户..."
python -c "
import os
from dotenv import load_dotenv
load_dotenv('.env.production')
from app import create_app
from app.extensions import db
from app.models import User
app = create_app('production')
with app.app_context():
    admin = User.query.filter_by(username='admin').first()
    if not admin:
        admin = User(
            username='admin',
            email='admin@example.com',
            password='admin',
            role='admin',
            is_active=True
        )
        db.session.add(admin)
        db.session.commit()
        print('管理员账户创建成功')
    else:
        print('管理员账户已存在')
" 2>/dev/null

# 停止现有服务
echo "🛑 停止现有服务..."
pkill -f "test_waitress.py" 2>/dev/null || true
pkill -f "python.*waitress" 2>/dev/null || true
sleep 1

# 启动服务
echo ""
echo "========================================"
echo "🚀 启动生产环境服务..."
echo "========================================"
echo ""

# 获取端口
PORT=$(grep FLASK_PORT .env.production | cut -d'=' -f2)

python test_waitress.py &
sleep 3

# 检查服务状态
if lsof -i:$PORT &>/dev/null; then
    echo ""
    echo "✅ 生产环境启动成功！"
    echo ""
    echo "访问地址："
    echo "  http://127.0.0.1:$PORT"
    echo ""
    echo "管理员账户："
    echo "  用户名: admin"
    echo "  密码: admin"
    echo "  ⚠️  请立即登录并修改密码！"
    echo ""
    echo "日志文件："
    echo "  logs/exam_system.log"
    echo ""
    echo "停止服务："
    echo "  pkill -f 'python.*waitress'"
    echo ""
else
    echo "❌ 服务启动失败，请检查日志"
    exit 1
fi
