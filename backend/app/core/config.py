"""Application settings loaded from environment / .env."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    anthropic_api_key: str = ""
    database_url: str = "postgresql+asyncpg://bobb:bobb@localhost:5432/bobb"
    fal_api_key: str = ""
    image_gen_provider: str = "fal"
    comfyui_url: str = "http://localhost:8188"
    redis_url: str = ""
    debug: bool = True
    port: int = 8420
    cache_dir: str = "cache/designs"


@lru_cache
def get_settings() -> Settings:
    return Settings()
