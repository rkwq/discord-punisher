import asyncio
from dataclasses import dataclass
from typing import Optional

import discord
import yt_dlp
from discord import app_commands
from discord.ext import commands


YTDL_OPTIONS = {
    "format": "bestaudio/best",
    "noplaylist": True,
    "quiet": True,
    "default_search": "ytsearch",
}

FFMPEG_OPTIONS = {
    "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
    "options": "-vn",
}


@dataclass
class Track:
    title: str
    webpage_url: str
    stream_url: str
    requested_by: str


class MusicPlayer:
    def __init__(self, bot: commands.Bot, guild_id: int) -> None:
        self.bot = bot
        self.guild_id = guild_id
        self.queue: asyncio.Queue[Track] = asyncio.Queue()
        self.current: Optional[Track] = None
        self.text_channel: Optional[discord.abc.Messageable] = None
        self.task: Optional[asyncio.Task] = None

    def start(self) -> None:
        if self.task is None or self.task.done():
            self.task = asyncio.create_task(self.player_loop())

    async def player_loop(self) -> None:
        await self.bot.wait_until_ready()
        while not self.bot.is_closed():
            self.current = await self.queue.get()
            guild = self.bot.get_guild(self.guild_id)
            voice_client = guild.voice_client if guild else None

            if voice_client is None or not voice_client.is_connected():
                self.queue.task_done()
                continue

            finished = asyncio.Event()

            def after_playback(error: Optional[Exception]) -> None:
                if error and self.text_channel:
                    asyncio.run_coroutine_threadsafe(
                        self.text_channel.send(f"Playback error: `{error}`"),
                        self.bot.loop,
                    )
                self.bot.loop.call_soon_threadsafe(finished.set)

            source = discord.FFmpegPCMAudio(self.current.stream_url, **FFMPEG_OPTIONS)
            voice_client.play(source, after=after_playback)

            if self.text_channel:
                await self.text_channel.send(f"Now playing: **{self.current.title}**")

            await finished.wait()
            self.queue.task_done()


class Music(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.players: dict[int, MusicPlayer] = {}

    def get_player(self, guild_id: int) -> MusicPlayer:
        player = self.players.get(guild_id)
        if player is None:
            player = MusicPlayer(self.bot, guild_id)
            self.players[guild_id] = player
        return player

    async def create_track(self, query: str, requested_by: str) -> Track:
        loop = asyncio.get_running_loop()

        def extract() -> dict:
            with yt_dlp.YoutubeDL(YTDL_OPTIONS) as ytdl:
                data = ytdl.extract_info(query, download=False)
                if "entries" in data:
                    data = data["entries"][0]
                return data

        data = await loop.run_in_executor(None, extract)
        return Track(
            title=data.get("title", "Unknown title"),
            webpage_url=data.get("webpage_url", query),
            stream_url=data["url"],
            requested_by=requested_by,
        )

    async def ensure_voice(self, interaction: discord.Interaction) -> Optional[discord.VoiceClient]:
        if interaction.guild is None:
            await interaction.response.send_message("Music commands only work in a server.", ephemeral=True)
            return None

        if not isinstance(interaction.user, discord.Member) or interaction.user.voice is None:
            await interaction.response.send_message("Join a voice channel first.", ephemeral=True)
            return None

        channel = interaction.user.voice.channel
        voice_client = interaction.guild.voice_client
        if voice_client is None:
            return await channel.connect()

        if voice_client.channel != channel:
            await voice_client.move_to(channel)

        return voice_client

    @app_commands.command(name="join", description="Join your current voice channel.")
    async def join(self, interaction: discord.Interaction) -> None:
        voice_client = await self.ensure_voice(interaction)
        if voice_client:
            await interaction.response.send_message(f"Joined `{voice_client.channel}`.")

    @app_commands.command(name="play", description="Play a song from a URL or search.")
    @app_commands.describe(query="A song URL or search text.")
    async def play(self, interaction: discord.Interaction, query: str) -> None:
        voice_client = await self.ensure_voice(interaction)
        if voice_client is None or interaction.guild is None:
            return

        await interaction.response.defer()
        track = await self.create_track(query, str(interaction.user))
        player = self.get_player(interaction.guild.id)
        player.text_channel = interaction.channel
        await player.queue.put(track)
        player.start()

        await interaction.followup.send(f"Queued: **{track.title}**")

    @app_commands.command(name="pause", description="Pause the current song.")
    async def pause(self, interaction: discord.Interaction) -> None:
        voice_client = interaction.guild.voice_client if interaction.guild else None
        if voice_client and voice_client.is_playing():
            voice_client.pause()
            await interaction.response.send_message("Paused.")
        else:
            await interaction.response.send_message("Nothing is playing.", ephemeral=True)

    @app_commands.command(name="resume", description="Resume paused music.")
    async def resume(self, interaction: discord.Interaction) -> None:
        voice_client = interaction.guild.voice_client if interaction.guild else None
        if voice_client and voice_client.is_paused():
            voice_client.resume()
            await interaction.response.send_message("Resumed.")
        else:
            await interaction.response.send_message("Nothing is paused.", ephemeral=True)

    @app_commands.command(name="skip", description="Skip the current song.")
    async def skip(self, interaction: discord.Interaction) -> None:
        voice_client = interaction.guild.voice_client if interaction.guild else None
        if voice_client and (voice_client.is_playing() or voice_client.is_paused()):
            voice_client.stop()
            await interaction.response.send_message("Skipped.")
        else:
            await interaction.response.send_message("Nothing is playing.", ephemeral=True)

    @app_commands.command(name="stop", description="Stop music and clear the queue.")
    async def stop(self, interaction: discord.Interaction) -> None:
        if interaction.guild is None:
            await interaction.response.send_message("Music commands only work in a server.", ephemeral=True)
            return

        player = self.get_player(interaction.guild.id)
        while not player.queue.empty():
            player.queue.get_nowait()
            player.queue.task_done()

        voice_client = interaction.guild.voice_client
        if voice_client:
            voice_client.stop()

        await interaction.response.send_message("Stopped and cleared the queue.")

    @app_commands.command(name="queue", description="Show the music queue.")
    async def queue(self, interaction: discord.Interaction) -> None:
        if interaction.guild is None:
            await interaction.response.send_message("Music commands only work in a server.", ephemeral=True)
            return

        player = self.get_player(interaction.guild.id)
        queued = list(player.queue._queue)

        lines = []
        if player.current:
            lines.append(f"Now: **{player.current.title}**")
        if queued:
            lines.extend(f"{index}. {track.title}" for index, track in enumerate(queued[:10], start=1))

        await interaction.response.send_message("\n".join(lines) if lines else "The queue is empty.")

    @app_commands.command(name="leave", description="Leave the voice channel.")
    async def leave(self, interaction: discord.Interaction) -> None:
        voice_client = interaction.guild.voice_client if interaction.guild else None
        if voice_client:
            await voice_client.disconnect()
            await interaction.response.send_message("Left the voice channel.")
        else:
            await interaction.response.send_message("I am not in a voice channel.", ephemeral=True)

    @commands.command(name="play")
    async def prefix_play(self, ctx: commands.Context, *, query: str) -> None:
        if ctx.guild is None or not isinstance(ctx.author, discord.Member) or ctx.author.voice is None:
            await ctx.reply("Join a voice channel first.", mention_author=False)
            return

        voice_client = ctx.guild.voice_client
        if voice_client is None:
            voice_client = await ctx.author.voice.channel.connect()
        elif voice_client.channel != ctx.author.voice.channel:
            await voice_client.move_to(ctx.author.voice.channel)

        message = await ctx.reply("Loading track...", mention_author=False)
        track = await self.create_track(query, str(ctx.author))
        player = self.get_player(ctx.guild.id)
        player.text_channel = ctx.channel
        await player.queue.put(track)
        player.start()
        await message.edit(content=f"Queued: **{track.title}**")

    @commands.command(name="join")
    async def prefix_join(self, ctx: commands.Context) -> None:
        if ctx.guild is None or not isinstance(ctx.author, discord.Member) or ctx.author.voice is None:
            await ctx.reply("Join a voice channel first.", mention_author=False)
            return

        voice_client = ctx.guild.voice_client
        if voice_client is None:
            voice_client = await ctx.author.voice.channel.connect()
        elif voice_client.channel != ctx.author.voice.channel:
            await voice_client.move_to(ctx.author.voice.channel)

        await ctx.reply(f"Joined `{voice_client.channel}`.", mention_author=False)

    @commands.command(name="pause")
    async def prefix_pause(self, ctx: commands.Context) -> None:
        voice_client = ctx.guild.voice_client if ctx.guild else None
        if voice_client and voice_client.is_playing():
            voice_client.pause()
            await ctx.reply("Paused.", mention_author=False)
        else:
            await ctx.reply("Nothing is playing.", mention_author=False)

    @commands.command(name="resume")
    async def prefix_resume(self, ctx: commands.Context) -> None:
        voice_client = ctx.guild.voice_client if ctx.guild else None
        if voice_client and voice_client.is_paused():
            voice_client.resume()
            await ctx.reply("Resumed.", mention_author=False)
        else:
            await ctx.reply("Nothing is paused.", mention_author=False)

    @commands.command(name="skip")
    async def prefix_skip(self, ctx: commands.Context) -> None:
        voice_client = ctx.guild.voice_client if ctx.guild else None
        if voice_client and (voice_client.is_playing() or voice_client.is_paused()):
            voice_client.stop()
            await ctx.reply("Skipped.", mention_author=False)
        else:
            await ctx.reply("Nothing is playing.", mention_author=False)

    @commands.command(name="stop")
    async def prefix_stop(self, ctx: commands.Context) -> None:
        if ctx.guild is None:
            await ctx.reply("Music commands only work in a server.", mention_author=False)
            return

        player = self.get_player(ctx.guild.id)
        while not player.queue.empty():
            player.queue.get_nowait()
            player.queue.task_done()

        voice_client = ctx.guild.voice_client
        if voice_client:
            voice_client.stop()

        await ctx.reply("Stopped and cleared the queue.", mention_author=False)

    @commands.command(name="queue")
    async def prefix_queue(self, ctx: commands.Context) -> None:
        if ctx.guild is None:
            await ctx.reply("Music commands only work in a server.", mention_author=False)
            return

        player = self.get_player(ctx.guild.id)
        queued = list(player.queue._queue)
        lines = []
        if player.current:
            lines.append(f"Now: **{player.current.title}**")
        if queued:
            lines.extend(f"{index}. {track.title}" for index, track in enumerate(queued[:10], start=1))

        await ctx.reply("\n".join(lines) if lines else "The queue is empty.", mention_author=False)

    @commands.command(name="leave")
    async def prefix_leave(self, ctx: commands.Context) -> None:
        voice_client = ctx.guild.voice_client if ctx.guild else None
        if voice_client:
            await voice_client.disconnect()
            await ctx.reply("Left the voice channel.", mention_author=False)
        else:
            await ctx.reply("I am not in a voice channel.", mention_author=False)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Music(bot))
