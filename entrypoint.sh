#!/bin/bash
set -e

echo "========================================="
echo "容器启动脚本"
echo "========================================="

# 等待数据库就绪
echo "等待数据库启动..."
MAX_ATTEMPTS=30
ATTEMPT=0

while [ $ATTEMPT -lt $MAX_ATTEMPTS ]; do
    if [ -n "$DATABASE_URL" ]; then
        # 从 DATABASE_URL 中提取数据库信息
        DB_HOST=$(echo $DATABASE_URL | sed -n 's/.*@\([^:]*\):.*/\1/p')
        DB_PORT=$(echo $DATABASE_URL | sed -n 's/.*:\([0-9]*\)\/.*/\1/p')
        DB_USER=$(echo $DATABASE_URL | sed -n 's/.*:\/\/\([^:]*\):.*/\1/p')
        DB_NAME=$(echo $DATABASE_URL | sed -n 's/.*\/\([^?]*\).*/\1/p')

        if [ -n "$DB_HOST" ] && [ -n "$DB_PORT" ]; then
            if nc -z $DB_HOST $DB_PORT 2>/dev/null; then
                echo "✅ 数据库已就绪 ($DB_HOST:$DB_PORT)"
                break
            fi
        fi
    fi

    ATTEMPT=$((ATTEMPT + 1))
    echo "等待中... ($ATTEMPT/$MAX_ATTEMPTS)"
    sleep 2
done

if [ $ATTEMPT -eq $MAX_ATTEMPTS ]; then
    echo "❌ 数据库连接超时"
    exit 1
fi

# 运行数据库迁移
echo ""
echo "运行数据库迁移..."
if flask db upgrade; then
    echo "✅ 数据库迁移完成"
else
    echo "❌ 数据库迁移失败"
    exit 1
fi

# 创建管理员账户（如果不存在）
echo ""
echo "检查管理员账户..."
if python create_admin.py; then
    echo "✅ 管理员账户检查完成"
else
    echo "⚠️  管理员账户检查失败（可能已存在）"
fi

echo ""
echo "========================================="
echo "启动应用服务..."
echo "========================================="

# 启动应用
exec "$@"
