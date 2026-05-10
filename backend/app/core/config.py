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

    storage_backend: str = Field(default="local", alias="STORAGE_BACKEND")
    s3_endpoint: str = Field(default="", alias="S3_ENDPOINT")
    s3_bucket: str = Field(default="factory-documents", alias="S3_BUCKET")
    s3_access_key: str = Field(default="", alias="S3_ACCESS_KEY")
    s3_secret_key: str = Field(default="", alias="S3_SECRET_KEY")
    s3_use_ssl: bool = Field(default=True, alias="S3_USE_SSL")

    wecom_webhook_url: str = Field(default="", alias="WECOM_WEBHOOK_URL")
    dingtalk_webhook_url: str = Field(default="", alias="DINGTALK_WEBHOOK_URL")
    integration_enabled: bool = Field(default=False, alias="INTEGRATION_ENABLED")
    integration_platform: str = Field(default="wecom", alias="INTEGRATION_PLATFORM")
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

    def ensure_runtime_dirs(self) -> None:
        """确保运行期目录存在，例如本地上传目录。"""
        self.upload_dir.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    """缓存配置对象，避免每次请求重复解析环境变量。"""
    return Settings()


settings = get_settings()
