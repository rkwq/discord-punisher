import os
from dataclasses import dataclass

from dotenv import load_dotenv


load_dotenv()


@dataclass(frozen=True)
class Settings:
    token: str
    command_prefix: str = "!"
    sync_commands: bool = True
    dashboard_enabled: bool = True
    guild_id: int | None = None


def load_settings() -> Settings:
    token = os.getenv("DISCORD_TOKEN", "").strip()
    command_prefix = os.getenv("COMMAND_PREFIX", "!").strip() or "!"
    sync_commands = os.getenv("SYNC_COMMANDS", "true").lower() in {"1", "true", "yes", "on"}
    dashboard_enabled = os.getenv("DASHBOARD_ENABLED", "true").lower() in {"1", "true", "yes", "on"}
    guild_id_str = os.getenv("GUILD_ID", "").strip()
    guild_id = int(guild_id_str) if guild_id_str.isdigit() else None

    if not token:
        raise RuntimeError("DISCORD_TOKEN is missing. Add it to your .env file.")

    return Settings(
        token=token,
        command_prefix=command_prefix,
        sync_commands=sync_commands,
        dashboard_enabled=dashboard_enabled,
        guild_id=guild_id,
    )
