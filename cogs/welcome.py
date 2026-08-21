import discord
from discord.ext import commands

from bot_config import load_bot_config, parse_color, parse_discord_id, render_template


class Welcome(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member) -> None:
        config = load_bot_config()["welcome"]
        if not config.get("enabled"):
            return

        channel_id = parse_discord_id(config.get("channel_id"))
        if channel_id is None:
            return

        channel = member.guild.get_channel(channel_id)
        if not isinstance(channel, discord.TextChannel):
            return

        values = {
            "member": member.mention,
            "name": member.display_name,
            "server": member.guild.name,
            "count": member.guild.member_count or "?",
        }
        embed = discord.Embed(
            title=render_template(config.get("title", ""), **values),
            description=render_template(config.get("message", ""), **values),
            color=parse_color(config.get("color")),
        )

        image_url = str(config.get("image_url", "")).strip()
        thumbnail_url = str(config.get("thumbnail_url", "")).strip()
        if image_url:
            embed.set_image(url=image_url)
        if thumbnail_url:
            embed.set_thumbnail(url=thumbnail_url)

        await channel.send(content=member.mention, embed=embed)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Welcome(bot))

