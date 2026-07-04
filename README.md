# AI 智能客服系统

> 基于 RAG 检索增强 + SSE 流式输出的微服务架构智能客服系统

## 技术栈

- **后端**：Python 3.12+ / FastAPI / aiomysql / redis.asyncio / ChromaDB / DashScope SDK
- **前端**：React 18 + Ant Design 5 + Vite
- **数据**：MySQL 8.0+ / Redis 6.0+ / ChromaDB（嵌入式向量库）
- **大模型**：DashScope 通义千问（qwen-turbo + text-embedding-v3）

## 项目结构

```
ai_customer_service/
├── backend/               # 后端 5 个微服务
│   ├── common/            # 公共模块（配置/数据库/Redis/JWT/响应）
│   ├── gateway/           # 网关 :8000（路由/鉴权/限流/CORS）
│   ├── user_service/      # 用户服务 :8001（注册/登录/JWT）
│   ├── chat_service/      # 对话服务 :8002（会话/消息/SSE）
│   ├── knowledge_service/ # 知识库服务 :8003（文档上传/入库）
│   ├── ai_service/        # AI 服务 :8004（RAG/流式生成/向量化）
│   ├── sql/init.sql       # 数据库建表脚本
│   └── scripts/           # 初始化脚本
└── frontend/              # 前端 React 应用
```

## 快速启动

### 1. 环境准备

确保已安装并运行：
- MySQL 8.0+
- Redis 6.0+
- Python 3.12+
- Node.js 18+

### 2. 配置环境变量

```bash
cd ai_customer_service
cp .env.example .env
# 编辑 .env，填写 MYSQL_PASSWORD、DASHSCOPE_API_KEY、JWT_SECRET_KEY
```

### 3. 初始化数据库

```bash
cd backend
pip install -r requirements.txt
python scripts/init_db.py      # 建库建表
python scripts/init_admin.py   # 初始化管理员和测试用户
```

### 4. 启动后端服务（各开一个终端）

```bash
cd backend
python -m user_service.main        # :8001
python -m chat_service.main        # :8002
python -m knowledge_service.main   # :8003
python -m ai_service.main          # :8004
python -m gateway.main             # :8000
```

### 5. 启动前端

```bash
cd frontend
npm install
npm run dev   # :5173
```

### 6. 访问系统

- 前端页面：http://localhost:5173
- API 文档：http://localhost:8000/docs

## 默认账户

| 角色 | 用户名 | 密码 | 说明 |
|------|--------|------|------|
| 管理员 | admin | admin123 | 可管理知识库和用户 |
| 普通用户 | testuser | user123 | 可使用客服对话 |

## 核心能力

- JWT 鉴权 + 网关统一路由
- RAG 检索增强问答（知识库文档检索 + LLM 生成）
- SSE 流式输出（打字机效果）
- 多轮对话上下文记忆
- 知识来源引用展示
- 文档上传与自动入库（PDF/TXT/DOCX）
