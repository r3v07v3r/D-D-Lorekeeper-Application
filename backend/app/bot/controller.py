"""Shared voice-control logic used by both the Discord slash commands
(app.bot.cogs.voice) and the GM-only FastAPI bot-control router
(app.routers.bot_control). Keeping this in one place means "join a channel"
or "start recording" behaves identically regardless of which surface
triggered it, and both surfaces share the same BotState (risk #7).
"""
import logging

import discord

from app.bot.recorder import VoiceRecorder
from app.config import Settings
from app.state import BotState

logger = logging.getLogger(__name__)


class VoiceControlError(Exception):
    """Raised for any expected/user-facing failure (not connected, no
    channel, already recording, etc.) so callers can show a friendly message
    instead of a raw traceback (risk #9).
    """


async def join_channel(bot_state: BotState, channel: discord.VoiceChannel) -> None:
    if bot_state.voice_client is not None and bot_state.voice_client.is_connected():
        raise VoiceControlError("Already connected to a voice channel - leave it first.")
    try:
        bot_state.voice_client = await channel.connect()
    except discord.ClientException as exc:
        raise VoiceControlError(f"Could not join voice channel: {exc}") from exc


async def leave_channel(bot_state: BotState) -> None:
    if bot_state.voice_client is None or not bot_state.voice_client.is_connected():
        raise VoiceControlError("Not currently connected to a voice channel.")
    if bot_state.is_recording:
        raise VoiceControlError("Stop recording before leaving the channel.")
    try:
        await bot_state.voice_client.disconnect()
    finally:
        bot_state.reset_voice()


async def start_recording(bot_state: BotState, session_log_id: int, settings: Settings) -> None:
    if bot_state.voice_client is None or not bot_state.voice_client.is_connected():
        raise VoiceControlError("Join a voice channel before starting a recording.")
    if bot_state.is_recording:
        raise VoiceControlError("Already recording.")

    recorder = VoiceRecorder(
        storage_dir=settings.audio_storage_dir,
        session_log_id=session_log_id,
        chunk_minutes=settings.recording_chunk_minutes,
    )
    try:
        recorder.start(bot_state.voice_client)
    except discord.sinks.RecordingException as exc:
        raise VoiceControlError(f"Could not start recording: {exc}") from exc

    bot_state.recorder = recorder
    bot_state.current_session_log_id = session_log_id
    bot_state.is_recording = True


async def stop_recording(bot_state: BotState) -> None:
    if not bot_state.is_recording or bot_state.recorder is None:
        raise VoiceControlError("Not currently recording.")
    await bot_state.recorder.stop()
    bot_state.recorder = None
    bot_state.is_recording = False
    bot_state.current_session_log_id = None
