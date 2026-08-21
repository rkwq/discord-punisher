import asyncio
import logging

import discord
from discord.ext import commands

from config import load_settings
from dashboard import start_dashboard_in_thread


COGS = (
    "cogs.general",
    "cogs.moderation",
    "cogs.music",
    "cogs.welcome",
    "cogs.role_request",
)


class GeneralBot(commands.Bot):
    def __init__(self) -> None:
        self.settings = load_settings()

        intents = discord.Intents.default()
        intents.guilds = True
        intents.members = True
        intents.message_content = True
        intents.voice_states = True

        super().__init__(
            command_prefix=self.settings.command_prefix,
            intents=intents,
            help_command=None,
        )

    async def setup_hook(self) -> None:
        for cog in COGS:
            try:
                await self.load_extension(cog)
                logging.info("Loaded cog: %s", cog)
            except Exception as exc:
                logging.error("Failed to load cog %s: %s", cog, exc)

        if self.settings.sync_commands:
            # Guild-specific sync is instant; global sync can take up to 1 hour
            guild_id = self.settings.guild_id
            if guild_id:
                guild = discord.Object(id=guild_id)
                self.tree.copy_global_to(guild=guild)
                guild_synced = await self.tree.sync(guild=guild)
                logging.info("Synced %s slash commands to guild %s.", len(guild_synced), guild_id)
            else:
                synced = await self.tree.sync()
                logging.info("Synced %s global slash commands.", len(synced))

    async def on_ready(self) -> None:
        if self.user is None:
            return

        logging.info("Logged in as %s (%s)", self.user, self.user.id)
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name="over the streets",
            )
        )


async def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    bot = GeneralBot()
    if bot.settings.dashboard_enabled:
        start_dashboard_in_thread()

    async with bot:
        await bot.start(bot.settings.token)


if __name__ == "__main__":
    asyncio.run(main())
