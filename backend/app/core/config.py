from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用配置，统一从环境变量或 .env 文件读取。"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = Field(default="FactoryOffice-Agent", alias="APP_NAME")
    app_env: str = Field(default="development", alias="APP_ENV")
    api_v1_prefix: str = Field(default="/api", alias="API_V1_PREFIX")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    frontend_base_url: str = Field(default="http://localhost:3000", alias="FRONTEND_BASE_URL")
    auth_secret_key: str = Field(default="dev-only-change-me", alias="AUTH_SECRET_KEY")
    encryption_key: str = Field(default="", alias="ENCRYPTION_KEY")

    database_url: str = Field(
        default="postgresql+psycopg://factory_user:factory_pass@localhost:5432/factory_agent",
        alias="DATABASE_URL",
    )

    upload_dir: Path = Field(default=Path("data/uploads"), alias="UPLOAD_DIR")

    llm_base_url: str = Field(default="", alias="LLM_BASE_URL")
    llm_api_key: str = Field(default="", alias="LLM_API_KEY")
    llm_model: str = Field(default="deepseek-chat", alias="LLM_MODEL")

    embedding_base_url: str = Field(default="", alias="EMBEDDING_BASE_URL")
    embedding_api_key: str = Field(default="", alias="EMBEDDING_API_KEY")
    embedding_model: str = Field(default="text-embedding-3-small", alias="EMBEDDING_MODEL")

    cors_origins: list[str] = Field(default=["*"], alias="CORS_ORIGINS")
    upload_max_size_mb: int = Field(default=50, ge=1, le=500, alias="UPLOAD_MAX_SIZE_MB")
    upload_chunk_size_bytes: int = Field(default=1024 * 1024, ge=64 * 1024, alias="UPLOAD_CHUNK_SIZE_BYTES")
    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")
    job_queue_name: str = Field(default="factoryoffice", alias="JOB_QUEUE_NAME")
    job_max_retries: int = Field(default=3, ge=0, le=20, alias="JOB_MAX_RETRIES")
    job_retry_intervals: str = Field(default="60,300,900", alias="JOB_RETRY_INTERVALS")
    job_scheduler_interval_seconds: int = Field(default=60, ge=10, le=3600, alias="JOB_SCHEDULER_INTERVAL_SECONDS")
    job_batch_size: int = Field(default=50, ge=1, le=1000, alias="JOB_BATCH_SIZE")

    @property
    def is_development(self) -> bool:
        """判断当前是否为本地开发环境。"""
        return self.app_env.lower() in {"dev", "development", "local"}

    @property
    def upload_max_size_bytes(self) -> int:
        """上传文件大小上限，单位字节。"""
        return self.upload_max_size_mb * 1024 * 1024

    @property
    def effective_cors_origins(self) -> list[str]:
        """生产环境不允许默认放开所有跨域来源。"""
        if self.is_development:
            return self.cors_origins
        if "*" in self.cors_origins:
            raise ValueError("生产环境必须显式配置 CORS_ORIGINS，不能使用 '*'。")
        return self.cors_origins

    @property
    def job_retry_intervals_seconds(self) -> list[int]:
        """解析 RQ 重试间隔，格式示例：60,300,900。"""
        intervals: list[int] = []
        for item in self.job_retry_intervals.split(","):
            item = item.strip()
            if not item:
                continue
            try:
                intervals.append(max(1, int(item)))
            except ValueError:
                continue
        return intervals or [60, 300, 900]

    def ensure_runtime_dirs(self) -> None:
        """确保运行期目录存在，例如本地上传目录。"""
        self.upload_dir.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    """缓存配置对象，避免每次请求重复解析环境变量。"""
    return Settings()


settings = get_settings()
