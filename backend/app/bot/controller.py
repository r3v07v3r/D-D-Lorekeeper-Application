"""Shared voice-control logic used by both the Discord slash commands
(app.bot.cogs.voice) and the GM-only FastAPI bot-control router
(app.routers.bot_control). Keeping this in one place means "join a channel"
or "start recording" behaves identically regardless of which surface
triggered it, and both surfaces share the same BotState (risk #7).
"""
import logging
from pathlib import Path

import discord

from app.bot.recorder import VoiceRecorder
from app.config import Settings
from app.runtime_config import RuntimeConfigStore
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
    # Seeds the initial membership snapshot immediately - on_voice_state_update
    # (see app/bot/client.py) only fires on the *next* join/leave/move, so
    # without this, anyone already sitting in the channel before the bot
    # joined would show as absent until they left and rejoined.
    bot_state.voice_member_discord_ids = {str(m.id) for m in channel.members if not m.bot}


async def leave_channel(bot_state: BotState) -> None:
    if bot_state.voice_client is None or not bot_state.voice_client.is_connected():
        raise VoiceControlError("Not currently connected to a voice channel.")
    if bot_state.is_recording:
        raise VoiceControlError("Stop recording before leaving the channel.")
    try:
        await bot_state.voice_client.disconnect()
    finally:
        bot_state.reset_voice()


async def start_recording(bot_state: BotState, session_log_id: int, settings: Settings | RuntimeConfigStore) -> None:
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


def play_clip(bot_state: BotState, file_path: Path, volume: float = 1.0) -> None:
    """Plays a soundboard clip into the connected voice channel.

    Independent of recording - verified against Pycord's VoiceClient source
    that play() only checks connection/is_playing state and start_recording()
    only checks connection/is_recording state, so a session recording in
    progress is completely unaffected by a sound effect playing over it (and
    vice versa): they're separate outbound/inbound audio streams.

    If a clip is already playing, it's stopped first rather than raising -
    on a soundboard, clicking a new sound while one is playing should
    interrupt it, not require an explicit "stop" click first.
    """
    if bot_state.voice_client is None or not bot_state.voice_client.is_connected():
        raise VoiceControlError("Join a voice channel before playing a sound.")
    if not file_path.exists():
        raise VoiceControlError(f"Sound file not found: {file_path.name}")

    if bot_state.voice_client.is_playing():
        bot_state.voice_client.stop()

    def _after_playback(error: Exception | None) -> None:
        if error is not None:
            logger.error("Soundboard playback error: %s", error)

    try:
        source = discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(str(file_path)), volume=volume)
        bot_state.voice_client.play(source, after=_after_playback)
    except discord.ClientException as exc:
        raise VoiceControlError(f"Could not play sound: {exc}") from exc


def stop_playback(bot_state: BotState) -> None:
    if bot_state.voice_client is None or not bot_state.voice_client.is_connected():
        raise VoiceControlError("Not currently connected to a voice channel.")
    if not bot_state.voice_client.is_playing():
        raise VoiceControlError("Nothing is currently playing.")
    bot_state.voice_client.stop()
