-- PostgreSQL 数据库初始化脚本
-- 此脚本在首次启动数据库容器时自动执行

-- 创建扩展
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- 创建函数：自动更新 updated_at 字段
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 创建数据库性能统计函数
CREATE OR REPLACE FUNCTION get_table_sizes()
RETURNS TABLE(
    tablename text,
    size_mb float
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        schemaname||'.'||tablename as tablename,
        pg_total_relation_size(schemaname||'.'||tablename)::float / 1024 / 1024 as size_mb
    FROM
        pg_tables
    WHERE
        schemaname NOT IN ('pg_catalog', 'information_schema')
    ORDER BY
        pg_total_relation_size(schemaname||'.'||tablename) DESC;
END;
$$ LANGUAGE plpgsql;

-- 创建函数：清理过期数据
CREATE OR REPLACE FUNCTION cleanup_expired_data(days_to_keep INTEGER DEFAULT 90)
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    -- 清理过期的会话数据（如果有）
    -- 根据实际情况调整表名和字段
    -- DELETE FROM sessions WHERE created_at < NOW() - INTERVAL '1 day' * days_to_keep;
    
    -- 清理过期的日志（如果有）
    -- DELETE FROM logs WHERE created_at < NOW() - INTERVAL '1 day' * days_to_keep;
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- 授权给应用用户
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO examuser;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO examuser;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO examuser;

-- 添加注释
COMMENT ON FUNCTION update_updated_at_column() IS '自动更新 updated_at 字段的触发器函数';
COMMENT ON FUNCTION get_table_sizes() IS '获取所有表的大小统计';
COMMENT ON FUNCTION cleanup_expired_data(INTEGER) IS '清理指定天数之前的过期数据';

-- 输出初始化完成信息
DO $$
BEGIN
    RAISE NOTICE '========================================';
    RAISE NOTICE '数据库初始化完成';
    RAISE NOTICE '数据库名: examdb';
    RAISE NOTICE '用户名: examuser';
    RAISE NOTICE '========================================';
END $$;
