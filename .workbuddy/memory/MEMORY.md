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

### 历史问题
- 2026-07-03 首跑遇到 "query 向量化超时"，疑 DashScope 网络或额度
