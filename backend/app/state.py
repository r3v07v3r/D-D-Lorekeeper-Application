"""Shared bot/recording state, explicitly passed around rather than accessed
as module-private globals (project risk #7). A single BotState instance
lives on app.state.bot_state; both the Discord cog and the FastAPI
bot_control router read/write it through this same object, so there is one
source of truth for "are we connected, what are we recording."
"""
from dataclasses import dataclass, field


@dataclass
class BotState:
    bot: object | None = None  # the running discord.Bot instance, set at startup
    bot_task: object | None = None  # asyncio.Task running bot.start(), set alongside `bot`
    voice_client: object | None = None  # discord.VoiceClient, set once connected
    current_session_log_id: int | None = None
    recorder: object | None = None  # app.bot.recorder.VoiceRecorder, set once recording starts
    is_recording: bool = False
    # Discord user IDs (as strings, matching User.discord_id's column type)
    # currently in the same voice channel as the bot - real Discord-voice
    # presence, kept fresh by on_voice_state_update (see app/bot/client.py)
    # and initialized on join (see app/bot/controller.py:join_channel).
    # Empty whenever the bot isn't connected to a channel.
    voice_member_discord_ids: set[str] = field(default_factory=set)

    def reset_voice(self) -> None:
        self.voice_client = None
        self.current_session_log_id = None
        self.recorder = None
        self.is_recording = False
        self.voice_member_discord_ids = set()
