-- 知识库权限改造：添加 owner_id 字段
-- owner_id IS NULL = 管理员创建（公共可见）
-- owner_id = 用户ID = 私有（仅自己可见）

ALTER TABLE knowledge_bases
    ADD COLUMN owner_id BIGINT DEFAULT NULL COMMENT '创建者ID，NULL=管理员(公共)'
    AFTER description;

-- 为已有数据设置 owner_id = NULL（保持公共可见）
-- UPDATE knowledge_bases SET owner_id = NULL WHERE owner_id IS NULL;

-- 索引：按创建者查询
ALTER TABLE knowledge_bases
    ADD INDEX idx_owner_id (owner_id);
