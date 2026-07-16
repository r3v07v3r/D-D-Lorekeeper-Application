"""Slash commands for manual voice control directly from Discord. These wrap
app.bot.controller so behavior matches the GM-only FastAPI bot-control
endpoints exactly. Every Discord API call is wrapped in try/except and
reported back via ctx.respond() rather than letting a raw traceback surface
in Discord (risk #9).
"""
import logging

import discord
from discord.ext import commands

from app.bot import controller
from app.database import SessionLocal
from app.models import SessionLog
from app.state import BotState

logger = logging.getLogger(__name__)


class VoiceCog(commands.Cog):
    def __init__(self, bot: discord.Bot, bot_state: BotState) -> None:
        self.bot = bot
        self.bot_state = bot_state

    @discord.slash_command(name="lk_join", description="Join your current voice channel")
    async def join(self, ctx: discord.ApplicationContext) -> None:
        if ctx.author.voice is None or ctx.author.voice.channel is None:
            await ctx.respond("You need to be in a voice channel first.", ephemeral=True)
            return
        try:
            await controller.join_channel(self.bot_state, ctx.author.voice.channel)
        except controller.VoiceControlError as exc:
            await ctx.respond(str(exc), ephemeral=True)
            return
        await ctx.respond(f"Joined {ctx.author.voice.channel.name}.")

    @discord.slash_command(name="lk_leave", description="Leave the current voice channel")
    async def leave(self, ctx: discord.ApplicationContext) -> None:
        try:
            await controller.leave_channel(self.bot_state)
        except controller.VoiceControlError as exc:
            await ctx.respond(str(exc), ephemeral=True)
            return
        await ctx.respond("Left the voice channel.")

    @discord.slash_command(name="lk_record_start", description="Start recording the current session")
    async def record_start(
        self,
        ctx: discord.ApplicationContext,
        session_number: discord.Option(int, "Session number"),
    ) -> None:
        # Local import to dodge a circular import: app.main imports
        # app.bot.client at module load time, which imports this module -
        # importing app.main back at module level here would cycle. By the
        # time a slash command actually runs, app.main is long since loaded.
        from app.main import app as fastapi_app

        runtime_config = fastapi_app.state.runtime_config
        if not runtime_config.active_campaign_id:
            await ctx.respond(
                "No active campaign is selected yet - pick one from the GM's dashboard first.",
                ephemeral=True,
            )
            return

        db = SessionLocal()
        try:
            log = SessionLog(
                campaign_id=runtime_config.active_campaign_id,
                session_number=session_number,
                date=discord.utils.utcnow().date(),
            )
            db.add(log)
            db.commit()
            db.refresh(log)
            session_log_id = log.id
        except Exception as exc:  # database failure - still report cleanly to Discord
            db.rollback()
            await ctx.respond(f"Could not create a session log: {exc}", ephemeral=True)
            return
        finally:
            db.close()

        try:
            await controller.start_recording(self.bot_state, session_log_id, runtime_config)
        except controller.VoiceControlError as exc:
            await ctx.respond(str(exc), ephemeral=True)
            return
        await ctx.respond(f"Recording started for session {session_number}.")

    @discord.slash_command(name="lk_record_stop", description="Stop recording the current session")
    async def record_stop(self, ctx: discord.ApplicationContext) -> None:
        try:
            await controller.stop_recording(self.bot_state)
        except controller.VoiceControlError as exc:
            await ctx.respond(str(exc), ephemeral=True)
            return
        await ctx.respond("Recording stopped.")


def register(bot: discord.Bot, bot_state: BotState) -> None:
    """Manually instantiates and registers the cog (not discord.py's
    load_extension-style `setup(bot)` hook, which we don't use here since we
    need to pass in the shared BotState too).
    """
    bot.add_cog(VoiceCog(bot, bot_state))
