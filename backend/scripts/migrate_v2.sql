-- ============================================================
-- 迁移脚本：为已有数据库添加 v2.0 新表
-- 直接执行即可，使用 IF NOT EXISTS 确保幂等
-- ============================================================

-- 1. sessions 表添加 mode 列（如果不存在）
ALTER TABLE sessions ADD COLUMN IF NOT EXISTS mode VARCHAR(20) NOT NULL DEFAULT 'kb' AFTER kb_id;

-- 2. 消息反馈表
CREATE TABLE IF NOT EXISTS message_feedback (
    feedback_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    message_id BIGINT NOT NULL,
    user_id BIGINT NOT NULL,
    rating TINYINT NOT NULL COMMENT '1=赞 0=踩',
    comment VARCHAR(500) DEFAULT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_msg_user (message_id, user_id),
    KEY idx_message_id (message_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='消息反馈表';

-- 3. 人工转接工单表
CREATE TABLE IF NOT EXISTS handoff_tickets (
    ticket_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    session_id BIGINT NOT NULL,
    user_id BIGINT NOT NULL,
    reason VARCHAR(500) DEFAULT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending' COMMENT 'pending/claimed/resolved/closed',
    claimed_by BIGINT DEFAULT NULL,
    resolution VARCHAR(1000) DEFAULT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    KEY idx_user_id (user_id),
    KEY idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='人工转接工单表';
