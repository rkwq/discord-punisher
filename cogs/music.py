import asyncio
import os
import re
from dataclasses import dataclass
from typing import Optional

import discord
import yt_dlp
from discord import app_commands
from discord.ext import commands

try:
    import spotipy
    from spotipy.oauth2 import SpotifyClientCredentials
    SPOTIPY_AVAILABLE = True
except ImportError:
    SPOTIPY_AVAILABLE = False


# ── Spotify helpers ──────────────────────────────────────────────────────────

SPOTIFY_TRACK_RE = re.compile(r"spotify\.com/track/([A-Za-z0-9]+)")
SPOTIFY_PLAYLIST_RE = re.compile(r"spotify\.com/playlist/([A-Za-z0-9]+)")
SPOTIFY_ALBUM_RE = re.compile(r"spotify\.com/album/([A-Za-z0-9]+)")


def _make_spotify() -> Optional["spotipy.Spotify"]:
    if not SPOTIPY_AVAILABLE:
        return None
    client_id = os.getenv("SPOTIFY_CLIENT_ID", "").strip()
    client_secret = os.getenv("SPOTIFY_CLIENT_SECRET", "").strip()
    if not client_id or not client_secret:
        return None
    auth = SpotifyClientCredentials(client_id=client_id, client_secret=client_secret)
    return spotipy.Spotify(auth_manager=auth)


def _track_query(track: dict) -> str:
    """Turn a Spotify track dict into a YouTube search string."""
    artists = ", ".join(a["name"] for a in track.get("artists", []))
    title = track.get("name", "")
    return f"{artists} - {title}"


def resolve_spotify(sp: "spotipy.Spotify", url_or_query: str) -> list[str]:
    """
    Given a Spotify URL or a plain search string, return a list of
    YouTube-ready search queries (one per track).
    """
    track_match = SPOTIFY_TRACK_RE.search(url_or_query)
    playlist_match = SPOTIFY_PLAYLIST_RE.search(url_or_query)
    album_match = SPOTIFY_ALBUM_RE.search(url_or_query)

    if track_match:
        track = sp.track(track_match.group(1))
        return [_track_query(track)]

    if playlist_match:
        results = sp.playlist_tracks(playlist_match.group(1), limit=25)
        queries = []
        for item in results.get("items", []):
            t = item.get("track")
            if t:
                queries.append(_track_query(t))
        return queries[:25]

    if album_match:
        results = sp.album_tracks(album_match.group(1), limit=25)
        queries = []
        for t in results.get("items", []):
            queries.append(_track_query(t))
        return queries[:25]

    # Plain text — treat as Spotify search
    results = sp.search(q=url_or_query, type="track", limit=1)
    items = results.get("tracks", {}).get("items", [])
    if items:
        return [_track_query(items[0])]

    return [url_or_query]  # fallback: pass straight to yt-dlp


# ── yt-dlp helpers ───────────────────────────────────────────────────────────

def _build_ytdl_options() -> dict:
    opts: dict = {
        "format": "bestaudio/best",
        "noplaylist": True,
        "quiet": True,
        "default_search": "ytsearch",
        "http_headers": {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/125.0.0.0 Safari/537.36"
            )
        },
    }
    cookies_file = os.getenv("YTDL_COOKIES_FILE", "").strip()
    if cookies_file and os.path.isfile(cookies_file):
        opts["cookiefile"] = cookies_file
    return opts


YTDL_OPTIONS = _build_ytdl_options()

FFMPEG_OPTIONS = {
    "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
    "options": "-vn",
}


# ── Data ─────────────────────────────────────────────────────────────────────

@dataclass
class Track:
    title: str
    webpage_url: str
    stream_url: str
    requested_by: str


# ── Player ───────────────────────────────────────────────────────────────────

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
                await self.text_channel.send(f"🎵 Now playing: **{self.current.title}**")

            await finished.wait()
            self.queue.task_done()


# ── Cog ──────────────────────────────────────────────────────────────────────

class Music(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.players: dict[int, MusicPlayer] = {}
        self.sp: Optional["spotipy.Spotify"] = _make_spotify()

        if self.sp:
            bot_name = "Punisher"
            print(f"[{bot_name}] Spotify integration enabled.")
        else:
            print("[Punisher] Spotify not configured — using YouTube search only.")

    def get_player(self, guild_id: int) -> MusicPlayer:
        if guild_id not in self.players:
            self.players[guild_id] = MusicPlayer(self.bot, guild_id)
        return self.players[guild_id]

    async def resolve_queries(self, query: str) -> list[str]:
        """Return a list of YouTube search strings for the given input."""
        if self.sp and ("spotify.com" in query or not query.startswith("http")):
            loop = asyncio.get_running_loop()
            try:
                queries = await loop.run_in_executor(None, resolve_spotify, self.sp, query)
                return queries
            except Exception as exc:
                print(f"Spotify resolve failed: {exc}")
        return [query]

    async def fetch_track(self, query: str, requested_by: str) -> Track:
        loop = asyncio.get_running_loop()

        def extract() -> dict:
            with yt_dlp.YoutubeDL(YTDL_OPTIONS) as ytdl:
                data = ytdl.extract_info(query, download=False)
                if "entries" in data:
                    data = data["entries"][0]
                return data

        data = await loop.run_in_executor(None, extract)
        return Track(
            title=data.get("title", "Unknown"),
            webpage_url=data.get("webpage_url", query),
            stream_url=data["url"],
            requested_by=requested_by,
        )

    async def ensure_voice(self, interaction: discord.Interaction) -> Optional[discord.VoiceClient]:
        if interaction.guild is None:
            await interaction.response.send_message("Music only works in a server.", ephemeral=True)
            return None
        if not isinstance(interaction.user, discord.Member) or interaction.user.voice is None:
            await interaction.response.send_message("Join a voice channel first.", ephemeral=True)
            return None
        channel = interaction.user.voice.channel
        vc = interaction.guild.voice_client
        if vc is None:
            return await channel.connect()
        if vc.channel != channel:
            await vc.move_to(channel)
        return vc

    # ── Slash commands ────────────────────────────────────────────────────────

    @app_commands.command(name="play", description="Play from Spotify link, Spotify search, or YouTube.")
    @app_commands.describe(query="Spotify link, song name, or YouTube URL.")
    async def play(self, interaction: discord.Interaction, query: str) -> None:
        vc = await self.ensure_voice(interaction)
        if vc is None or interaction.guild is None:
            return

        await interaction.response.defer()

        queries = await self.resolve_queries(query)
        player = self.get_player(interaction.guild.id)
        player.text_channel = interaction.channel

        if len(queries) == 1:
            try:
                track = await self.fetch_track(queries[0], str(interaction.user))
            except Exception as exc:
                await interaction.followup.send(f"❌ Could not load track: `{exc}`", ephemeral=True)
                return
            await player.queue.put(track)
            player.start()
            await interaction.followup.send(f"✅ Queued: **{track.title}**")
        else:
            await interaction.followup.send(f"📋 Loading **{len(queries)}** tracks from Spotify...")
            loaded = 0
            for q in queries:
                try:
                    track = await self.fetch_track(q, str(interaction.user))
                    await player.queue.put(track)
                    loaded += 1
                except Exception:
                    pass
            player.start()
            await interaction.channel.send(f"✅ Queued **{loaded}/{len(queries)}** tracks.")

    @app_commands.command(name="pause", description="Pause the current song.")
    async def pause(self, interaction: discord.Interaction) -> None:
        vc = interaction.guild.voice_client if interaction.guild else None
        if vc and vc.is_playing():
            vc.pause()
            await interaction.response.send_message("⏸ Paused.")
        else:
            await interaction.response.send_message("Nothing is playing.", ephemeral=True)

    @app_commands.command(name="resume", description="Resume paused music.")
    async def resume(self, interaction: discord.Interaction) -> None:
        vc = interaction.guild.voice_client if interaction.guild else None
        if vc and vc.is_paused():
            vc.resume()
            await interaction.response.send_message("▶️ Resumed.")
        else:
            await interaction.response.send_message("Nothing is paused.", ephemeral=True)

    @app_commands.command(name="skip", description="Skip the current song.")
    async def skip(self, interaction: discord.Interaction) -> None:
        vc = interaction.guild.voice_client if interaction.guild else None
        if vc and (vc.is_playing() or vc.is_paused()):
            vc.stop()
            await interaction.response.send_message("⏭ Skipped.")
        else:
            await interaction.response.send_message("Nothing is playing.", ephemeral=True)

    @app_commands.command(name="stop", description="Stop music and clear the queue.")
    async def stop(self, interaction: discord.Interaction) -> None:
        if interaction.guild is None:
            return
        player = self.get_player(interaction.guild.id)
        while not player.queue.empty():
            player.queue.get_nowait()
            player.queue.task_done()
        vc = interaction.guild.voice_client
        if vc:
            vc.stop()
        await interaction.response.send_message("⏹ Stopped and cleared the queue.")

    @app_commands.command(name="queue", description="Show the current music queue.")
    async def show_queue(self, interaction: discord.Interaction) -> None:
        if interaction.guild is None:
            return
        player = self.get_player(interaction.guild.id)
        queued = list(player.queue._queue)
        lines = []
        if player.current:
            lines.append(f"🎵 **Now playing:** {player.current.title}")
        if queued:
            lines.extend(f"`{i}.` {t.title}" for i, t in enumerate(queued[:10], 1))
            if len(queued) > 10:
                lines.append(f"*...and {len(queued) - 10} more*")
        await interaction.response.send_message("\n".join(lines) if lines else "The queue is empty.")

    @app_commands.command(name="leave", description="Leave the voice channel.")
    async def leave(self, interaction: discord.Interaction) -> None:
        vc = interaction.guild.voice_client if interaction.guild else None
        if vc:
            await vc.disconnect()
            await interaction.response.send_message("👋 Left.")
        else:
            await interaction.response.send_message("I'm not in a voice channel.", ephemeral=True)

    @app_commands.command(name="join", description="Join your voice channel.")
    async def join(self, interaction: discord.Interaction) -> None:
        vc = await self.ensure_voice(interaction)
        if vc:
            await interaction.response.send_message(f"Joined `{vc.channel}`.")

    # ── Prefix mirrors ────────────────────────────────────────────────────────

    @commands.command(name="play")
    async def prefix_play(self, ctx: commands.Context, *, query: str) -> None:
        if ctx.guild is None or not isinstance(ctx.author, discord.Member) or ctx.author.voice is None:
            await ctx.reply("Join a voice channel first.", mention_author=False)
            return
        vc = ctx.guild.voice_client
        if vc is None:
            vc = await ctx.author.voice.channel.connect()
        elif vc.channel != ctx.author.voice.channel:
            await vc.move_to(ctx.author.voice.channel)

        msg = await ctx.reply("🔍 Resolving...", mention_author=False)
        queries = await self.resolve_queries(query)
        player = self.get_player(ctx.guild.id)
        player.text_channel = ctx.channel

        if len(queries) == 1:
            try:
                track = await self.fetch_track(queries[0], str(ctx.author))
            except Exception as exc:
                await msg.edit(content=f"❌ {exc}")
                return
            await player.queue.put(track)
            player.start()
            await msg.edit(content=f"✅ Queued: **{track.title}**")
        else:
            await msg.edit(content=f"📋 Loading **{len(queries)}** tracks...")
            loaded = 0
            for q in queries:
                try:
                    track = await self.fetch_track(q, str(ctx.author))
                    await player.queue.put(track)
                    loaded += 1
                except Exception:
                    pass
            player.start()
            await msg.edit(content=f"✅ Queued **{loaded}/{len(queries)}** tracks.")

    @commands.command(name="skip")
    async def prefix_skip(self, ctx: commands.Context) -> None:
        vc = ctx.guild.voice_client if ctx.guild else None
        if vc and (vc.is_playing() or vc.is_paused()):
            vc.stop()
            await ctx.reply("⏭ Skipped.", mention_author=False)

    @commands.command(name="stop")
    async def prefix_stop(self, ctx: commands.Context) -> None:
        if ctx.guild is None:
            return
        player = self.get_player(ctx.guild.id)
        while not player.queue.empty():
            player.queue.get_nowait()
            player.queue.task_done()
        vc = ctx.guild.voice_client
        if vc:
            vc.stop()
        await ctx.reply("⏹ Stopped.", mention_author=False)

    @commands.command(name="pause")
    async def prefix_pause(self, ctx: commands.Context) -> None:
        vc = ctx.guild.voice_client if ctx.guild else None
        if vc and vc.is_playing():
            vc.pause()
            await ctx.reply("⏸ Paused.", mention_author=False)

    @commands.command(name="resume")
    async def prefix_resume(self, ctx: commands.Context) -> None:
        vc = ctx.guild.voice_client if ctx.guild else None
        if vc and vc.is_paused():
            vc.resume()
            await ctx.reply("▶️ Resumed.", mention_author=False)

    @commands.command(name="queue")
    async def prefix_queue(self, ctx: commands.Context) -> None:
        if ctx.guild is None:
            return
        player = self.get_player(ctx.guild.id)
        queued = list(player.queue._queue)
        lines = []
        if player.current:
            lines.append(f"🎵 **Now:** {player.current.title}")
        if queued:
            lines.extend(f"`{i}.` {t.title}" for i, t in enumerate(queued[:10], 1))
        await ctx.reply("\n".join(lines) if lines else "Queue is empty.", mention_author=False)

    @commands.command(name="leave")
    async def prefix_leave(self, ctx: commands.Context) -> None:
        vc = ctx.guild.voice_client if ctx.guild else None
        if vc:
            await vc.disconnect()
            await ctx.reply("👋 Left.", mention_author=False)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Music(bot))
