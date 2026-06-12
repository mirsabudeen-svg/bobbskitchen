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

    # ── Sprint 9: Twilio WhatsApp ─────────────────────────────────────────────
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_whatsapp_from: str = "whatsapp:+14155238886"  # Twilio sandbox default
    twilio_template_sid_en: str = ""   # approved EN template SID (HX...)
    twilio_template_sid_ml: str = ""   # approved ML template SID (HX...)
    public_media_base_url: str = ""    # e.g. https://cdn.bobb.ai (HTTPS, no auth)

    @property
    def whatsapp_enabled(self) -> bool:
        """True only when all required Twilio credentials are present."""
        return bool(
            self.twilio_account_sid
            and self.twilio_auth_token
            and self.twilio_whatsapp_from
            and (self.twilio_template_sid_en or self.twilio_template_sid_ml)
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()

