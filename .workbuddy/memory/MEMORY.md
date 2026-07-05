# 项目长期记忆

## AI 智能客服系统 (E:\Z_myfile\ai_customer_service)

### 技术栈
- 后端: Fastapi 微服务 (gateway:8000 + user:8001 + chat:8002 + knowledge:8003 + ai:8004)
- 前端: React 18 + Ant Design 5 + Vite (:5173)
- 数据: MySQL 8.0 + Redis 6 + **SQLite + numpy**（替代 ChromaDB） + DashScope (通义千问)

### 环境约定
- Python 依赖管理：**用 uv**（已装 uv 0.11.26，位于 `D:\DevelopPython\uv.exe`），不用裸 pip
  - venv 实际建在**项目根目录** `E:\Z_myfile\ai_customer_service\.venv`（不是 backend 下），Python 3.13.12
- 依赖已装齐（fastapi 0.139 / uvicorn 0.50 / numpy 2.x / dashscope 1.26.2 等，chromadb 1.5.9 已安装但不再使用）
- 启动服务命令要用根目录 venv：`E:\Z_myfile\ai_customer_service\.venv\Scripts\python.exe -m xxx_service.main`
- MySQL 安装在 `D:\mytools\mysql-8.0.31-winx64\`，服务名 `MySQL`，root 密码非空
- Redis 已作为本地进程运行（redis-server.exe），但 cli 不在 PATH

### 配置坑
- `backend/common/config.py` 的 `env_file=".env"` 是相对路径，必须在 `backend/` 目录下运行命令，.env 放 backend 根目录
- README 说 admin 脚本在 `scripts/init/`，实际在 `scripts/` 平铺

### 架构特点
- **向量存储：SQLite + numpy**（替代 ChromaDB）：knowledge_service 用 SQLite 存储向量数据（JSON 序列化），用 numpy 计算余弦相似度。纯 Python 实现，无 Rust/C++ 依赖，不会 segfault。ai_service 通过 HTTP `/api/knowledge/search|count` 远程调用
- **双模式对话**：sessions 表有 `mode` 字段（kb/assistant）
  - kb 模式：严格 RAG，知识库无内容则回答"不知道"
  - assistant 模式：DashScope enable_search=True（qwen-plus 联网搜索增强）
- **前端 FormData 修复**：request.js 自动检测 FormData时不设 Content-Type
- **启动时自动重试**：knowledge_service 启动时自动重试所有 pending/failed 文档入库

### 历史问题
- 2026-07-03 首跑遇到 "query 向量化超时"，疑 DashScope 网络或额度
- 2026-07-05 发现 DashScope SDK 1.26.2 的 `response.output` 返回 dict 不是对象 → 已修复
- 2026-07-05 发现 httpx 连接池 keep-alive 死连接 → 已修复（禁用 keep-alive）
- 2026-07-05 发现 aiomysql 连接池泄漏 → 已修复（正确调用 `pool_ctx.__aexit__`）
- 2026-07-05 Windows `localhost` 解析优先 IPv6 → 已改 .env 所有地址为 `127.0.0.1`
- 2026-07-05 **ChromaDB 1.5.9 Rust 后端在 Python 3.13 + Windows 上 segfault**：`collection.add()` 段错误（exit 139/0xC0000005）。PersistentClient/EphemeralClient/RustClient/HttpClient+Server 全部段错误。降级到 0.6.x 也失败（hnswlib 无 Python 3.13 wheel）。**最终用 SQLite + numpy 替代 ChromaDB**（纯 Python，无 native 依赖）
- 2026-07-05 知识库为空时改为通用助手模式
- 2026-07-05 `add_chunks()` 失败时不抛异常 → ingest 继续标记 "ready" → 已修复（返回 bool + ingest 检查）
- 2026-07-05 `chroma_worker.py` 的 `_do_add_chunks()` 用 `get_collection()` → collection 不存在时崩溃 → 已改 `get_or_create_collection()`
- Windows + uvicorn reload=True + TimedRotatingFileHandler 跨零点会报 WinError 32，不影响业务
