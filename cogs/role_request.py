import discord
from discord import app_commands
from discord.ext import commands

from bot_config import load_bot_config, parse_color, parse_discord_id


CUSTOM_ID = "general_bot:role_request"


class RoleRequestModal(discord.ui.Modal):
    def __init__(self, bot: commands.Bot, config: dict) -> None:
        super().__init__(title=str(config.get("form_title", "Role Request Form"))[:45])
        self.bot = bot
        self.config = config
        self.inputs: list[discord.ui.TextInput] = []

        for index, field in enumerate(config.get("fields", [])[:5]):
            label = str(field.get("label") or f"Field {index + 1}")[:45]
            text_input = discord.ui.TextInput(
                label=label,
                placeholder=str(field.get("placeholder") or "")[:100],
                required=bool(field.get("required", True)),
                max_length=300,
            )
            self.inputs.append(text_input)
            self.add_item(text_input)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        if interaction.guild is None:
            await interaction.response.send_message("This can only be submitted in a server.", ephemeral=True)
            return

        channel_id = parse_discord_id(self.config.get("submission_channel_id"))
        submission_channel = interaction.guild.get_channel(channel_id) if channel_id else interaction.channel
        if not isinstance(submission_channel, discord.TextChannel):
            await interaction.response.send_message("The request log channel is not configured correctly.", ephemeral=True)
            return

        embed = discord.Embed(
            title="New Role Request",
            description=f"Submitted by {interaction.user.mention}",
            color=parse_color("#FEE75C", 0xFEE75C),
        )
        embed.set_author(name=str(interaction.user), icon_url=interaction.user.display_avatar.url)

        for item in self.inputs:
            embed.add_field(name=item.label, value=item.value or "Not provided", inline=False)

        assign_role_id = parse_discord_id(self.config.get("assign_role_id"))
        if assign_role_id:
            role = interaction.guild.get_role(assign_role_id)
            if role:
                embed.add_field(name="Requested Role", value=role.mention, inline=False)

        reviewer_role_id = parse_discord_id(self.config.get("reviewer_role_id"))
        mention = ""
        if reviewer_role_id:
            role = interaction.guild.get_role(reviewer_role_id)
            if role:
                mention = role.mention

        await submission_channel.send(content=mention, embed=embed, allowed_mentions=discord.AllowedMentions(roles=True))
        await interaction.response.send_message("Your role request was submitted.", ephemeral=True)


class RoleRequestView(discord.ui.View):
    def __init__(self, bot: commands.Bot) -> None:
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(
        label="Submit Request",
        emoji="📝",
        style=discord.ButtonStyle.blurple,
        custom_id=CUSTOM_ID,
    )
    async def submit_request(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        config = load_bot_config()["role_request"]
        if not config.get("enabled"):
            await interaction.response.send_message("Role requests are currently closed.", ephemeral=True)
            return

        fields = config.get("fields", [])[:5]
        if not fields:
            await interaction.response.send_message("The role request form has no fields configured.", ephemeral=True)
            return

        button.label = str(config.get("button_label") or "Submit Request")[:80]
        button.emoji = str(config.get("button_emoji") or "📝")[:32]
        await interaction.response.send_modal(RoleRequestModal(self.bot, config))


class RoleRequest(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    async def cog_load(self) -> None:
        self.bot.add_view(RoleRequestView(self.bot))

    def build_panel_embed(self, guild: discord.Guild, config: dict) -> discord.Embed:
        embed = discord.Embed(
            title=str(config.get("panel_title") or "Role Request System"),
            description=str(config.get("panel_message") or "Click the button below to request a role."),
            color=parse_color(config.get("color"), 0xED4245),
        )
        warning = str(config.get("form_warning", "")).strip()
        if warning:
            embed.add_field(name="Before You Submit", value=warning, inline=False)
        embed.set_footer(text=f"{guild.name} role request system")

        image_url = str(config.get("panel_image_url", "")).strip()
        thumbnail_url = str(config.get("panel_thumbnail_url", "")).strip()
        if image_url:
            embed.set_image(url=image_url)
        if thumbnail_url:
            embed.set_thumbnail(url=thumbnail_url)

        return embed

    @app_commands.command(name="role_request_panel", description="Post the configured role request panel.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def role_request_panel(self, interaction: discord.Interaction) -> None:
        if interaction.guild is None:
            await interaction.response.send_message("This only works in a server.", ephemeral=True)
            return

        config = load_bot_config()["role_request"]
        channel_id = parse_discord_id(config.get("panel_channel_id"))
        channel = interaction.guild.get_channel(channel_id) if channel_id else interaction.channel
        if not isinstance(channel, discord.TextChannel):
            await interaction.response.send_message("The panel channel is not configured correctly.", ephemeral=True)
            return

        view = RoleRequestView(self.bot)
        view.children[0].label = str(config.get("button_label") or "Submit Request")[:80]
        view.children[0].emoji = str(config.get("button_emoji") or "📝")[:32]
        await channel.send(embed=self.build_panel_embed(interaction.guild, config), view=view)
        await interaction.response.send_message(f"Role request panel posted in {channel.mention}.", ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(RoleRequest(bot))
