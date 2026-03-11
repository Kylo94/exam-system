#!/bin/bash

# 数据库迁移脚本

set -e

# 颜色输出
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo "========================================"
echo "数据库迁移脚本"
echo "========================================"
echo ""

# 检查 Flask 应用
if ! command -v flask &> /dev/null; then
    echo -e "${RED}错误: flask 命令未找到${NC}"
    echo "请确保已安装 Flask: pip install Flask"
    exit 1
fi

# 检查环境变量
if [ -z "$FLASK_APP" ]; then
    export FLASK_APP=run.py
fi

if [ -z "$FLASK_ENV" ]; then
    export FLASK_ENV=development
fi

echo "当前配置:"
echo "  FLASK_APP: $FLASK_APP"
echo "  FLASK_ENV: $FLASK_ENV"
echo ""

# 检查数据库连接
echo "检查数据库连接..."
if flask db current &>/dev/null; then
    echo -e "${GREEN}✅ 数据库连接正常${NC}"
else
    echo -e "${RED}❌ 数据库连接失败${NC}"
    echo "请检查 DATABASE_URL 环境变量"
    exit 1
fi

# 显示当前版本
echo ""
echo "当前数据库版本:"
flask db current

# 检查是否有待应用的迁移
echo ""
echo "检查待应用的迁移..."
LATEST_REVISION=$(flask db heads | grep -oP '\([a-f0-9]+\)' | head -1)
CURRENT_REVISION=$(flask db current | grep -oP '\([a-f0-9]+\)' || echo "")

if [ "$LATEST_REVISION" != "$CURRENT_REVISION" ]; then
    echo -e "${YELLOW}发现新的迁移版本${NC}"

    # 显示迁移历史
    echo ""
    echo "迁移历史:"
    flask db history

    # 确认是否执行迁移
    echo ""
    read -p "是否执行数据库迁移? (y/n) " -n 1 -r
    echo

    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "正在执行迁移..."
        if flask db upgrade; then
            echo -e "${GREEN}✅ 数据库迁移成功${NC}"
            echo ""
            echo "新的数据库版本:"
            flask db current
        else
            echo -e "${RED}❌ 数据库迁移失败${NC}"
            exit 1
        fi
    else
        echo "迁移已取消"
        exit 0
    fi
else
    echo -e "${GREEN}✅ 数据库已是最新版本${NC}"
fi

echo ""
echo "========================================"
echo "迁移脚本执行完成"
echo "========================================"
