import discord
from discord import app_commands
from discord.ext import commands


class General(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="ping", description="Check whether the bot is responsive.")
    async def slash_ping(self, interaction: discord.Interaction) -> None:
        latency_ms = round(self.bot.latency * 1000)
        await interaction.response.send_message(f"Pong. `{latency_ms}ms`")

    @commands.command(name="ping")
    async def prefix_ping(self, ctx: commands.Context) -> None:
        latency_ms = round(self.bot.latency * 1000)
        await ctx.reply(f"Pong. `{latency_ms}ms`", mention_author=False)

    @app_commands.command(name="about", description="Show what this bot can do.")
    async def about(self, interaction: discord.Interaction) -> None:
        embed = discord.Embed(
            title="General Discord Bot",
            description="Moderation, basic music, and clean room to grow.",
            color=discord.Color.blurple(),
        )
        embed.add_field(
            name="Moderation",
            value="`/purge`, `/timeout`, `/untimeout`, `/kick`, `/ban`, `/unban`",
            inline=False,
        )
        embed.add_field(
            name="Music",
            value="`/join`, `/play`, `/pause`, `/resume`, `/skip`, `/stop`, `/queue`, `/leave`",
            inline=False,
        )
        await interaction.response.send_message(embed=embed)

    @commands.command(name="help")
    async def prefix_help(self, ctx: commands.Context) -> None:
        embed = discord.Embed(
            title="Bot Commands",
            description="Use slash commands or the same names with your prefix.",
            color=discord.Color.blurple(),
        )
        embed.add_field(
            name="Moderation",
            value="purge, timeout, untimeout, kick, ban, unban",
            inline=False,
        )
        embed.add_field(
            name="Music",
            value="join, play, pause, resume, skip, stop, queue, leave",
            inline=False,
        )
        await ctx.reply(embed=embed, mention_author=False)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(General(bot))

