"""Creates the Pycord Bot instance and registers cogs. The bot runs in the
same asyncio event loop as FastAPI (started as a background task from
main.py's startup event) rather than as a separate process, so bot_control
routes can directly call into app.bot.controller.
"""
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

    register_voice_cog(bot, bot_state)
    return bot
