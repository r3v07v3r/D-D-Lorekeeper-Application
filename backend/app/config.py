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

    # Summarization provider: "openai" (paid, hosted) or "ollama" (free,
    # local - see app/ai/summarization.py). Ollama exposes an OpenAI-compatible
    # endpoint, so the same `openai` SDK client works for both; only the
    # base_url/api_key differ (see app/ai/pipeline.py's build_llm_client()).
    llm_provider: str = "openai"
    ollama_base_url: str = "http://localhost:11434/v1"

    # Transcription provider: "openai" (Whisper API, paid) or "local"
    # (faster-whisper, free, runs on this machine - see app/ai/transcription.py).
    transcription_provider: str = "openai"
    local_whisper_model_size: str = "small"

    dndbeyond_sync_interval_minutes: int = 15

    # Which Campaign (see app/models.py) new sessions are created under and
    # GET /sessions returns - see app/routers/campaigns.py. None until the
    # GM has picked or created one.
    active_campaign_id: int | None = None

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.audio_storage_dir.mkdir(parents=True, exist_ok=True)
    return settings
