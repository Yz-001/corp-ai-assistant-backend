"""Application configuration module."""

from functools import lru_cache
from typing import Literal

from pydantic import Field, PostgresDsn, RedisDsn
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = "AI Enterprise Assistant"
    app_env: Literal["dev", "test", "prod"] = "dev"
    app_port: int = 8000
    debug: bool = False

    # Database
    postgres_dsn: PostgresDsn = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/ai_assistant"
    )
    sqlite_dsn: str = "sqlite+aiosqlite:///./data/app.db"
    use_sqlite: bool = True
    db_echo: bool = False

    # Redis
    redis_url: RedisDsn = Field(default="redis://localhost:6379/0")
    redis_password: str | None = None

    # JWT
    jwt_secret: str = "your-super-secret-key-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 10080  # 7 days
    jwt_refresh_expire_minutes: int = 20160  # 14 days

    @property
    def JWT_ACCESS_TOKEN_EXPIRES(self) -> int:
        """JWT access token expires in seconds."""
        return self.jwt_expire_minutes * 60

    @property
    def JWT_REFRESH_TOKEN_EXPIRES(self) -> int:
        """JWT refresh token expires in seconds."""
        return self.jwt_refresh_expire_minutes * 60

    @property
    def JWT_ACCESS_TOKEN_EXPIRES_SECONDS(self) -> int:
        """JWT access token expires in seconds."""
        return self.jwt_expire_minutes * 60

    # LLM
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    llm_model_name: str = "gpt-4o-mini"
    embedding_model_name: str = "text-embedding-3-small"

    # Vector Store
    vector_store_provider: Literal["chroma", "qdrant", "milvus"] = "chroma"
    chroma_persist_dir: str = "./data/chroma"
    chroma_host: str = "localhost"
    chroma_port: int = 8000

    # Object Storage
    object_storage_provider: Literal["local", "minio", "s3"] = "local"
    upload_dir: str = "./data/uploads"
    max_upload_size_mb: int = 20

    # MinIO / S3
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = ""
    minio_secret_key: str = ""
    minio_bucket: str = "ai-assistant"
    minio_secure: bool = False

    # RAG
    default_top_k: int = 5
    chunk_size: int = 500
    chunk_overlap: int = 50

    # Timeouts
    chat_timeout_seconds: int = 60
    tool_timeout_seconds: int = 15
    mcp_timeout_seconds: int = 20

    # Online User
    online_user_ttl_seconds: int = 300  # 5 minutes
    active_user_ttl_seconds: int = 1800  # 30 minutes

    # Celery
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"

    @property
    def database_url(self) -> str:
        """Get database URL as string."""
        if self.use_sqlite:
            return self.sqlite_dsn
        return str(self.postgres_dsn)

    @property
    def redis_dsn_str(self) -> str:
        """Get Redis DSN as string."""
        return str(self.redis_url)

    @property
    def is_dev(self) -> bool:
        """Check if running in development mode."""
        return self.app_env == "dev"

    @property
    def is_prod(self) -> bool:
        """Check if running in production mode."""
        return self.app_env == "prod"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()