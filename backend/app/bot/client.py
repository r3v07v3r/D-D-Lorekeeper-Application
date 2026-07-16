"""Creates the Pycord Bot instance and registers cogs. The bot runs in the
same asyncio event loop as FastAPI (started as a background task from
main.py's startup event) rather than as a separate process, so bot_control
routes can directly call into app.bot.controller.
"""
import asyncio
import logging

import discord

from app.bot.cogs.voice import register as register_voice_cog
from app.state import BotState

logger = logging.getLogger(__name__)


def create_bot(bot_state: BotState) -> discord.Bot:
    intents = discord.Intents.default()
    intents.voice_states = True
    intents.members = True

    bot = discord.Bot(intents=intents)

    @bot.event
    async def on_ready() -> None:
        logger.info("Discord bot logged in as %s", bot.user)

    @bot.event
    async def on_voice_state_update(
        member: discord.Member, before: discord.VoiceState, after: discord.VoiceState
    ) -> None:
        """Keeps BotState.voice_member_discord_ids in sync with who's
        actually in the bot's own voice channel - real Discord-voice
        presence (see app/routers/users.py:get_voice_presence), as opposed
        to the app-connectivity presence SessionStore already tracks.
        Recomputes the full membership from the channel itself rather than
        patching the set incrementally, since that's correct regardless of
        which side of the join/leave/move this event represents.
        """
        if bot_state.voice_client is None or not bot_state.voice_client.is_connected():
            return
        channel = bot_state.voice_client.channel
        if before.channel != channel and after.channel != channel:
            return  # unrelated to the channel the bot is actually in
        bot_state.voice_member_discord_ids = {str(m.id) for m in channel.members if not m.bot}

    register_voice_cog(bot, bot_state)
    return bot


async def ensure_bot_running(bot_state: BotState, discord_bot_token: str) -> None:
    """Starts the bot if a token is configured and it isn't already running.

    Shared by main.py's startup (token present in persisted settings/env at
    boot) and the Settings API (GM pastes in a token after the app is
    already running) - both paths need identical "start if not started"
    behavior, so it lives in one place rather than being duplicated.
    """
    if bot_state.bot is not None or not discord_bot_token:
        return

    bot = create_bot(bot_state)
    bot_state.bot = bot
    bot_state.bot_task = asyncio.create_task(bot.start(discord_bot_token))
