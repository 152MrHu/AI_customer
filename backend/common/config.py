"""统一配置管理 - 基于 pydantic-settings 从环境变量读取"""
from pathlib import Path
from pydantic_settings import BaseSettings
from pydantic import Field

# 项目根目录（backend/ 的父目录），确保所有相对路径以此为基准
# 无论从哪个目录启动服务，都使用同一个绝对路径
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    # MySQL
    MYSQL_HOST: str = "localhost"
    MYSQL_PORT: int = 3306
    MYSQL_USER: str = "root"
    MYSQL_PASSWORD: str = "1234"
    MYSQL_DATABASE: str = "ai_customer_service"

    # Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str = ""

    # JWT
    JWT_SECRET_KEY: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_HOURS: int = 24
    JWT_REMEMBER_HOURS: int = 168

    # DashScope
    DASHSCOPE_API_KEY: str = ""
    LLM_MODEL: str = "qwen-turbo"
    EMBEDDING_MODEL: str = "text-embedding-v3"

    # ChromaDB / 向量数据（使用绝对路径，确保不同工作目录启动时一致）
    CHROMA_PERSIST_PATH: str = str(_PROJECT_ROOT / "chroma_data")

    # 文件上传（使用绝对路径）
    UPLOAD_DIR: str = str(_PROJECT_ROOT / "uploads")

    # CORS
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000"

    # AI 参数
    AI_TIMEOUT: int = 30
    RATE_LIMIT_PER_MIN: int = 10
    TOP_K: int = 5
    SIMILARITY_THRESHOLD: float = 0.5
    MAX_TOKENS: int = 8192

    # 文档切块
    CHUNK_SIZE: int = 600
    CHUNK_OVERLAP: int = 100

    # 服务地址
    USER_SERVICE_URL: str = "http://localhost:8001"
    CHAT_SERVICE_URL: str = "http://localhost:8002"
    KNOWLEDGE_SERVICE_URL: str = "http://localhost:8003"
    AI_SERVICE_URL: str = "http://localhost:8004"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    @property
    def upload_dir_path(self) -> Path:
        p = Path(self.UPLOAD_DIR)
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def chroma_path(self) -> str:
        p = Path(self.CHROMA_PERSIST_PATH)
        p.mkdir(parents=True, exist_ok=True)
        return str(p.resolve())

    class Config:
        # .env 文件在 backend/ 目录下，使用绝对路径避免工作目录问题
        env_file = str(_PROJECT_ROOT / "backend" / ".env")
        env_file_encoding = "utf-8"


settings = Settings()
