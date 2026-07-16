"""GM-only settings: Discord bot token, OpenAI API key, campaign passphrase,
and a few tunables, editable from the dashboard instead of requiring a
hand-edited .env file (the packaged single-file Electron build doesn't ship
with one - see app/runtime_config.py for why this exists).

Secrets are write-only through this API: GET never echoes back a token,
key, or passphrase, only whether one is currently set, so a leaked
screenshot or a non-GM peeking at network traffic (which they can't anyway -
GM-only, and now passphrase-gated too - see app.auth.require_network_access)
doesn't expose the actual value.
"""
import os

import httpx
from fastapi import APIRouter, Depends, Request

from app.auth import SessionRecord, require_gm
from app.bot.client import ensure_bot_running
from app.netinfo import detect_lan_ip, detect_public_ip
from app.routers.bot_control import get_bot_state
from app.runtime_config import RuntimeConfigStore, get_runtime_config
from app.schemas import SettingsPublic, SettingsUpdate, SetupItem
from app.state import BotState

router = APIRouter(prefix="/settings", tags=["settings"])


def _check_ollama_reachable(base_url: str) -> bool:
    """A bare TCP connect wouldn't distinguish "Ollama" from anything else
    listening on that port, so this hits its OpenAI-compatible /models
    endpoint instead. Short timeout since this runs synchronously on every
    Settings page load whenever Ollama is the selected provider.
    """
    try:
        response = httpx.get(f"{base_url.rstrip('/')}/models", timeout=1.5)
        return response.status_code == 200
    except httpx.HTTPError:
        return False


def _compute_setup_items(config: RuntimeConfigStore) -> list[SetupItem]:
    """Everything the GM hasn't finished configuring yet, for the dashboard's
    "setup outstanding" banner (see frontend/src/components/SetupBanner.tsx).
    Kept here rather than in the frontend so there's one source of truth for
    what "configured" means per field, instead of duplicating this logic in
    both languages.
    """
    items: list[SetupItem] = []

    if not config.is_set("discord_bot_token"):
        items.append(
            SetupItem(
                key="discord_bot_token",
                severity="required",
                message="Discord bot token isn't set - the bot can't join voice channels or record sessions.",
            )
        )

    needs_openai_key = (
        config.transcription_provider == "openai" or config.llm_provider == "openai"
    ) and not config.is_set("openai_api_key")
    if needs_openai_key:
        items.append(
            SetupItem(
                key="openai_api_key",
                severity="required",
                message="OpenAI API key isn't set, but the OpenAI provider is selected for transcription and/or summarization.",
            )
        )

    if config.llm_provider == "ollama" and not _check_ollama_reachable(config.ollama_base_url):
        items.append(
            SetupItem(
                key="ollama",
                severity="required",
                message="Ollama isn't reachable - make sure it's installed, running, and the URL in Settings is correct.",
            )
        )

    if not config.has_passphrase():
        items.append(
            SetupItem(
                key="campaign_passphrase",
                severity="optional",
                message="No campaign passphrase set - only this computer can log in until you set one (only needed to play with others).",
            )
        )

    return items


def _to_public(config: RuntimeConfigStore, bot_state: BotState, request: Request) -> SettingsPublic:
    return SettingsPublic(
        discord_bot_token_set=config.is_set("discord_bot_token"),
        openai_api_key_set=config.is_set("openai_api_key"),
        whisper_model=config.whisper_model,
        summarization_model=config.summarization_model,
        llm_provider=config.llm_provider,
        ollama_base_url=config.ollama_base_url,
        transcription_provider=config.transcription_provider,
        local_whisper_model_size=config.local_whisper_model_size,
        recording_chunk_minutes=config.recording_chunk_minutes,
        dndbeyond_sync_interval_minutes=config.dndbeyond_sync_interval_minutes,
        bot_running=bot_state.bot is not None,
        campaign_passphrase_set=config.has_passphrase(),
        detected_lan_ip=detect_lan_ip(),
        detected_public_ip=detect_public_ip(),
        certificate_fingerprint=request.app.state.tls_fingerprint,
        server_port=int(os.environ.get("LOREKEEPER_PORT", "8000")),
        setup_items=_compute_setup_items(config),
    )


@router.get("", response_model=SettingsPublic)
def get_settings_view(
    request: Request,
    config: RuntimeConfigStore = Depends(get_runtime_config),
    bot_state: BotState = Depends(get_bot_state),
    _current: SessionRecord = Depends(require_gm),
) -> SettingsPublic:
    return _to_public(config, bot_state, request)


@router.put("", response_model=SettingsPublic)
async def update_settings(
    payload: SettingsUpdate,
    request: Request,
    config: RuntimeConfigStore = Depends(get_runtime_config),
    bot_state: BotState = Depends(get_bot_state),
    _current: SessionRecord = Depends(require_gm),
) -> SettingsPublic:
    fields = payload.model_dump(exclude_unset=True)
    passphrase = fields.pop("campaign_passphrase", None)
    config.update(**fields)
    if passphrase is not None:
        config.set_passphrase(passphrase)

    # If the GM just pasted in a token and the bot isn't running yet, start
    # it now rather than requiring an app restart.
    await ensure_bot_running(bot_state, config.discord_bot_token)

    return _to_public(config, bot_state, request)
