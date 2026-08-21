from datetime import timedelta

import discord
from discord import app_commands
from discord.ext import commands


def moderator_only() -> app_commands.check:
    async def predicate(interaction: discord.Interaction) -> bool:
        permissions = interaction.user.guild_permissions
        return permissions.manage_messages or permissions.moderate_members or permissions.administrator

    return app_commands.check(predicate)


class Moderation(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="purge", description="Delete recent messages from this channel.")
    @app_commands.describe(amount="How many messages to delete, from 1 to 100.")
    @app_commands.checks.has_permissions(manage_messages=True)
    async def purge(self, interaction: discord.Interaction, amount: app_commands.Range[int, 1, 100]) -> None:
        if not isinstance(interaction.channel, discord.TextChannel):
            await interaction.response.send_message("This only works in a server text channel.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)
        deleted = await interaction.channel.purge(limit=amount)
        await interaction.followup.send(f"Deleted `{len(deleted)}` messages.", ephemeral=True)

    @commands.command(name="purge")
    @commands.has_permissions(manage_messages=True)
    async def prefix_purge(self, ctx: commands.Context, amount: int) -> None:
        amount = max(1, min(amount, 100))
        deleted = await ctx.channel.purge(limit=amount + 1)
        await ctx.send(f"Deleted `{len(deleted) - 1}` messages.", delete_after=5)

    @app_commands.command(name="timeout", description="Timeout a member.")
    @app_commands.describe(member="Member to timeout.", minutes="Timeout length in minutes.", reason="Reason for the timeout.")
    @app_commands.checks.has_permissions(moderate_members=True)
    async def timeout(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        minutes: app_commands.Range[int, 1, 40320],
        reason: str = "No reason provided.",
    ) -> None:
        until = discord.utils.utcnow() + timedelta(minutes=minutes)
        await member.timeout(until, reason=reason)
        await interaction.response.send_message(f"Timed out {member.mention} for `{minutes}` minutes. Reason: {reason}")

    @commands.command(name="timeout")
    @commands.has_permissions(moderate_members=True)
    async def prefix_timeout(self, ctx: commands.Context, member: discord.Member, minutes: int, *, reason: str = "No reason provided.") -> None:
        minutes = max(1, min(minutes, 40320))
        until = discord.utils.utcnow() + timedelta(minutes=minutes)
        await member.timeout(until, reason=reason)
        await ctx.reply(f"Timed out {member.mention} for `{minutes}` minutes. Reason: {reason}", mention_author=False)

    @app_commands.command(name="untimeout", description="Remove a member's timeout.")
    @app_commands.describe(member="Member to untimeout.", reason="Reason for removing timeout.")
    @app_commands.checks.has_permissions(moderate_members=True)
    async def untimeout(self, interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided.") -> None:
        await member.timeout(None, reason=reason)
        await interaction.response.send_message(f"Removed timeout from {member.mention}.")

    @commands.command(name="untimeout")
    @commands.has_permissions(moderate_members=True)
    async def prefix_untimeout(self, ctx: commands.Context, member: discord.Member, *, reason: str = "No reason provided.") -> None:
        await member.timeout(None, reason=reason)
        await ctx.reply(f"Removed timeout from {member.mention}.", mention_author=False)

    @app_commands.command(name="kick", description="Kick a member.")
    @app_commands.describe(member="Member to kick.", reason="Reason for the kick.")
    @app_commands.checks.has_permissions(kick_members=True)
    async def kick(self, interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided.") -> None:
        await member.kick(reason=reason)
        await interaction.response.send_message(f"Kicked `{member}`. Reason: {reason}")

    @commands.command(name="kick")
    @commands.has_permissions(kick_members=True)
    async def prefix_kick(self, ctx: commands.Context, member: discord.Member, *, reason: str = "No reason provided.") -> None:
        await member.kick(reason=reason)
        await ctx.reply(f"Kicked `{member}`. Reason: {reason}", mention_author=False)

    @app_commands.command(name="ban", description="Ban a member.")
    @app_commands.describe(member="Member to ban.", reason="Reason for the ban.")
    @app_commands.checks.has_permissions(ban_members=True)
    async def ban(self, interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided.") -> None:
        await member.ban(reason=reason)
        await interaction.response.send_message(f"Banned `{member}`. Reason: {reason}")

    @commands.command(name="ban")
    @commands.has_permissions(ban_members=True)
    async def prefix_ban(self, ctx: commands.Context, member: discord.Member, *, reason: str = "No reason provided.") -> None:
        await member.ban(reason=reason)
        await ctx.reply(f"Banned `{member}`. Reason: {reason}", mention_author=False)

    @app_commands.command(name="unban", description="Unban a user by ID.")
    @app_commands.describe(user_id="The banned user's Discord ID.", reason="Reason for unbanning.")
    @app_commands.checks.has_permissions(ban_members=True)
    async def unban(self, interaction: discord.Interaction, user_id: str, reason: str = "No reason provided.") -> None:
        user = await self.bot.fetch_user(int(user_id))
        await interaction.guild.unban(user, reason=reason)
        await interaction.response.send_message(f"Unbanned `{user}`.")

    @commands.command(name="unban")
    @commands.has_permissions(ban_members=True)
    async def prefix_unban(self, ctx: commands.Context, user_id: int, *, reason: str = "No reason provided.") -> None:
        user = await self.bot.fetch_user(user_id)
        await ctx.guild.unban(user, reason=reason)
        await ctx.reply(f"Unbanned `{user}`.", mention_author=False)

    @purge.error
    @timeout.error
    @untimeout.error
    @kick.error
    @ban.error
    @unban.error
    async def on_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError) -> None:
        message = "You do not have permission to use that command."
        if isinstance(error, app_commands.BotMissingPermissions):
            message = "I do not have the permissions needed for that."
        elif isinstance(error, app_commands.CommandInvokeError):
            message = f"Command failed: {error.original}"

        if interaction.response.is_done():
            await interaction.followup.send(message, ephemeral=True)
        else:
            await interaction.response.send_message(message, ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Moderation(bot))

