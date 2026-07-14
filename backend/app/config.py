"""Environment-driven settings, loaded once and shared via get_settings()."""
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    discord_bot_token: str = ""
    database_url: str = "sqlite:///./lorekeeper.db"
    audio_storage_dir: Path = Path("./recordings")
    recording_chunk_minutes: int = 5
    # "null" is required, not optional, for the packaged Electron app: pages
    # loaded via file:// send a literal "Origin: null" header (verified
    # against this backend's CORSMiddleware - see risk #8), not "file://".
    # Without it, every authenticated request (they all carry an Authorization
    # header, which forces a CORS preflight) is rejected by the browser once
    # packaged, even though plain curl/server-side calls appear to work.
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173,null"

    openai_api_key: str = ""
    whisper_model: str = "whisper-1"
    summarization_model: str = "gpt-4o"

    dndbeyond_sync_interval_minutes: int = 15

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.audio_storage_dir.mkdir(parents=True, exist_ok=True)
    return settings
