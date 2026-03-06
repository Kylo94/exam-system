#!/bin/bash

# ========================================
# 数据库备份脚本
# ========================================

set -e

# 配置
BACKUP_DIR="./backups/postgres"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="examdb_backup_${TIMESTAMP}.sql"
RETENTION_DAYS=7

# 颜色输出
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 创建备份目录
mkdir -p "$BACKUP_DIR"

log_info "开始备份数据库..."

# 检查数据库容器是否运行
if ! docker ps | grep -q exam-postgres; then
    log_error "数据库容器未运行"
    exit 1
fi

# 执行备份
docker exec exam-postgres pg_dump -U examuser examdb > "${BACKUP_DIR}/${BACKUP_FILE}"

if [ $? -eq 0 ]; then
    log_info "备份成功: ${BACKUP_DIR}/${BACKUP_FILE}"

    # 压缩备份文件
    gzip "${BACKUP_DIR}/${BACKUP_FILE}"
    log_info "压缩完成: ${BACKUP_DIR}/${BACKUP_FILE}.gz"

    # 清理旧备份
    log_info "清理 ${RETENTION_DAYS} 天前的备份..."
    find "$BACKUP_DIR" -name "examdb_backup_*.sql.gz" -mtime +${RETENTION_DAYS} -delete

    # 显示备份信息
    BACKUP_SIZE=$(du -h "${BACKUP_DIR}/${BACKUP_FILE}.gz" | cut -f1)
    log_info "备份大小: $BACKUP_SIZE"
else
    log_error "备份失败"
    exit 1
fi
