#!/bin/bash

# ========================================
# 在线答题系统 - Docker 镜像构建脚本
# ========================================
# 使用方法：
#   开发环境镜像：./scripts/build-image.sh dev
#   生产环境镜像：./scripts/build-image.sh prod

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

# 检查 Docker 是否安装
if ! command -v docker &> /dev/null; then
    echo -e "${RED}错误: Docker 未安装${NC}"
    echo "请先安装 Docker: https://docs.docker.com/get-docker/"
    exit 1
fi

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  在线答题系统 - Docker 镜像构建${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# 检查构建参数
BUILD_TYPE=${1:-prod}

if [[ "$BUILD_TYPE" != "dev" && "$BUILD_TYPE" != "prod" ]]; then
    echo -e "${RED}错误: 无效的构建类型 '$BUILD_TYPE'${NC}"
    echo "使用方法: $0 [dev|prod]"
    echo ""
    echo "示例："
    echo "  $0 dev   # 构建开发环境镜像"
    echo "  $0 prod  # 构建生产环境镜像"
    exit 1
fi

# 镜像配置
if [[ "$BUILD_TYPE" == "dev" ]]; then
    IMAGE_NAME="exam-system:dev"
    BUILD_ARGS="--build-arg BUILD_ENV=development"
    echo -e "${YELLOW}构建类型: 开发环境${NC}"
elif [[ "$BUILD_TYPE" == "prod" ]]; then
    IMAGE_NAME="exam-system:latest"
    BUILD_ARGS="--build-arg BUILD_ENV=production"
    echo -e "${YELLOW}构建类型: 生产环境${NC}"
fi

echo -e "${YELLOW}镜像名称: $IMAGE_NAME${NC}"
echo ""

# 检查 Dockerfile 是否存在
if [[ ! -f "$PROJECT_DIR/Dockerfile" ]]; then
    echo -e "${RED}错误: Dockerfile 不存在${NC}"
    exit 1
fi

# 清理旧镜像
echo -e "${YELLOW}清理旧镜像...${NC}"
docker rmi $IMAGE_NAME 2>/dev/null || true

# 构建镜像
echo ""
echo -e "${GREEN}开始构建镜像...${NC}"
echo ""

docker build $BUILD_ARGS -t $IMAGE_NAME .

# 检查构建结果
if [[ $? -eq 0 ]]; then
    echo ""
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}  镜像构建成功！${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo ""
    echo -e "${YELLOW}镜像信息:${NC}"
    docker images $IMAGE_NAME

    echo ""
    echo -e "${GREEN}下一步操作:${NC}"
    if [[ "$BUILD_TYPE" == "dev" ]]; then
        echo -e "  启动开发环境: docker-compose up -d"
    else
        echo -e "  启动生产环境: docker-compose -f docker-compose.prod.yml up -d"
    fi
    echo ""
else
    echo ""
    echo -e "${RED}镜像构建失败！${NC}"
    exit 1
fi
