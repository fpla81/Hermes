from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    real_capture: bool = Field(default=False, validation_alias="BEMTEVI_REAL_CAPTURE")
    lookup_url_template: str | None = Field(
        default=None, validation_alias="BEMTEVI_LOOKUP_URL_TEMPLATE"
    )
    profile_dir: str = Field(
        default="./bem_te_vi_profile",
        validation_alias="BEM_TE_VI_PROFILE_DIR",
    )
    headless: bool = Field(default=True, validation_alias="BEMTEVI_HEADLESS")
    nav_timeout_ms: int = Field(default=30_000, validation_alias="BEMTEVI_NAV_TIMEOUT")


@lru_cache
def get_settings() -> Settings:
    return Settings()
