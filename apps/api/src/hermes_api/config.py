from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = Field(
        default="postgresql+asyncpg://hermes:hermes@localhost:5432/hermes",
        validation_alias="DATABASE_URL",
    )
    database_url_sync: str = Field(
        default="postgresql://hermes:hermes@localhost:5432/hermes",
        validation_alias="DATABASE_URL_SYNC",
    )
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        validation_alias="REDIS_URL",
    )
    celery_broker_url: str = Field(
        default="redis://localhost:6379/1",
        validation_alias="CELERY_BROKER_URL",
    )
    celery_result_backend: str = Field(
        default="redis://localhost:6379/2",
        validation_alias="CELERY_RESULT_BACKEND",
    )
    cors_origins: str = Field(
        default="http://localhost:3000",
        validation_alias="CORS_ORIGINS",
    )
    gemini_api_key: str | None = Field(default=None, validation_alias="GEMINI_API_KEY")
    gemini_model: str = Field(default="gemini-2.5-flash", validation_alias="GEMINI_MODEL")
    gemini_anonymizer_model: str = Field(
        default="gemini-2.5-flash", validation_alias="GEMINI_ANONYMIZER_MODEL"
    )
    gemini_read_timeout: float = Field(
        default=600.0, validation_alias="GEMINI_READ_TIMEOUT"
    )
    gemini_connect_timeout: float = Field(
        default=15.0, validation_alias="GEMINI_CONNECT_TIMEOUT"
    )
    gemini_max_retries: int = Field(
        default=2, validation_alias="GEMINI_MAX_RETRIES"
    )
    llm_response_cache_enabled: bool = Field(
        default=True, validation_alias="LLM_RESPONSE_CACHE_ENABLED"
    )
    llm_response_cache_ttl: int = Field(
        default=604800, validation_alias="LLM_RESPONSE_CACHE_TTL"
    )
    gemini_context_cache_enabled: bool = Field(
        default=True, validation_alias="GEMINI_CONTEXT_CACHE_ENABLED"
    )
    gemini_context_cache_ttl: int = Field(
        default=3600, validation_alias="GEMINI_CONTEXT_CACHE_TTL"
    )
    internal_secret: str | None = Field(
        default=None, validation_alias="HERMES_INTERNAL_SECRET"
    )
    playwright_service_url: str = Field(
        default="http://localhost:8001",
        validation_alias="PLAYWRIGHT_SERVICE_URL",
    )

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
