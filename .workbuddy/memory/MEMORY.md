# 项目长期记忆

## AI 智能客服系统 (E:\Z_myfile\ai_customer_service)

### 技术栈
- 后端: Fastapi 微服务 (gateway:8000 + user:8001 + chat:8002 + knowledge:8003 + ai:8004)
- 前端: React 18 + Ant Design 5 + Vite (:5173)
- 数据: MySQL 8.0 + Redis 6 + ChromaDB (嵌入式向量库) + DashScope (通义千问)

### 环境约定
- Python 依赖管理：**用 uv**（已装 uv 0.11.26，位于 `D:\DevelopPython\uv.exe`），不用裸 pip
  - venv 实际建在**项目根目录** `E:\Z_myfile\ai_customer_service\.venv`（不是 backend 下），Python 3.13.12
- 依赖已装齐（fastapi 0.139 / uvicorn 0.50 / chromadb 1.5.9 / dashscope 1.26.2 等）
- 启动服务命令要用根目录 venv：`E:\Z_myfile\ai_customer_service\.venv\Scripts\python.exe -m xxx_service.main`
- MySQL 安装在 `D:\mytools\mysql-8.0.31-winx64\`，服务名 `MySQL`，root 密码非空
- Redis 已作为本地进程运行（redis-server.exe），但 cli 不在 PATH

### 配置坑
- `backend/common/config.py` 的 `env_file=".env"` 是相对路径，必须在 `backend/` 目录下运行命令，.env 放 backend 根目录
- README 说 admin 脚本在 `scripts/init/`，实际在 `scripts/` 平铺

### 架构特点
- **ChromaDB 单进程架构**：只有 knowledge_service 直接操作 ChromaDB，ai_service 通过 HTTP `/api/knowledge/search|count` 远程调用（避免多进程文件锁冲突）
- **双模式对话**：sessions 表有 `mode` 字段（kb/assistant）
  - kb 模式：严格 RAG，知识库无内容则回答"不知道"
  - assistant 模式：DashScope enable_search=True（qwen-plus 联网搜索增强）
- **前端 FormData 修复**：request.js 自动检测 FormData时不设 Content-Type

### 历史问题
- 2026-07-03 首跑遇到 "query 向量化超时"，疑 DashScope 网络或额度
- 2026-07-05 发现 DashScope SDK 1.26.2 的 `response.output` 返回 dict 不是对象，`ai_service/adapter/dashscope_adapter.py` 的属性访问会失败 → 已修复（兼容 dict）
- 2026-07-05 发现 httpx 连接池 keep-alive 死连接问题：下游服务 reload 后 gateway 等复用死连接报 5002 → 已修复（`common/http_client.py` 禁用 keep-alive）
- 2026-07-05 发现 aiomysql 连接池泄漏：`common/database.py` 的 `DB.__aexit__` 调用 `conn.close()` 关闭物理连接但未调用 `pool.acquire().__aexit__()` → 连接永远不释放回池，约10次DB操作后池耗尽，所有后续请求 hang → 已修复（改为正确调用 `pool_ctx.__aexit__`）
- 2026-07-05 Windows `localhost` 解析优先 IPv6 `::1`：uvicorn 绑 `0.0.0.0`（仅IPv4），httpx/aiomysql/redis 解析 localhost 优先试 `::1` → 已改 .env 和 config 所有服务地址/数据库地址为 `127.0.0.1`
- 2026-07-05 ChromaDB 多进程锁冲突：ai_service 和 knowledge_service 同时用 PersistentClient 访问同一目录 → SQLite/WAL 文件锁 hang 死 → 已修复为**单进程架构**：只有 knowledge_service 直接操作 ChromaDB，ai_service 通过 HTTP `/api/knowledge/search|count` 远程调用
- 2026-07-05 知识库为空时改为通用助手模式：不再返回 5003 错误，而是跳过 RAG 检索直接调 LLM 对话
- Windows + uvicorn reload=True + TimedRotatingFileHandler 跨零点会报 WinError 32（日志轮转失败），不影响业务
