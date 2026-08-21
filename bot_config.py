import json
from copy import deepcopy
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = BASE_DIR / "data" / "config.json"


DEFAULT_CONFIG: dict[str, Any] = {
    "welcome": {
        "enabled": False,
        "channel_id": "",
        "title": "Welcome to {server}",
        "message": "Welcome {member}. We are glad you joined.",
        "image_url": "",
        "thumbnail_url": "",
        "color": "#5865F2",
    },
    "role_request": {
        "enabled": True,
        "panel_channel_id": "",
        "submission_channel_id": "",
        "reviewer_role_id": "",
        "assign_role_id": "",
        "panel_title": "Role Request System",
        "panel_message": "Fill your data correctly from the button.",
        "panel_image_url": "",
        "panel_thumbnail_url": "",
        "color": "#C81E3A",
        "button_label": "Submit Request",
        "button_emoji": "📝",
        "form_title": "Role Request Form",
        "form_warning": "Do not share passwords or other sensitive information.",
        "fields": [
            {"label": "Your Name (In-game name)", "placeholder": "Enter your in-game name", "required": True},
            {"label": "Your ID", "placeholder": "Enter your character ID", "required": True},
            {"label": "Level in City", "placeholder": "Enter your current level", "required": True},
            {"label": "Rank in Family", "placeholder": "Enter your desired rank", "required": True},
            {"label": "Forum Account Link", "placeholder": "Enter your forum account link", "required": True},
        ],
    },
}


def ensure_config_file() -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not CONFIG_PATH.exists():
        save_config(DEFAULT_CONFIG)


def merge_defaults(config: dict[str, Any], defaults: dict[str, Any]) -> dict[str, Any]:
    merged = deepcopy(defaults)
    for key, value in config.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = merge_defaults(value, merged[key])
        else:
            merged[key] = value
    return merged


def load_bot_config() -> dict[str, Any]:
    ensure_config_file()
    with CONFIG_PATH.open("r", encoding="utf-8") as file:
        loaded = json.load(file)
    return merge_defaults(loaded, DEFAULT_CONFIG)


def save_config(config: dict[str, Any]) -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with CONFIG_PATH.open("w", encoding="utf-8") as file:
        json.dump(config, file, indent=2)
        file.write("\n")


def parse_discord_id(value: Any) -> int | None:
    text = str(value or "").strip()
    if not text:
        return None
    if text.startswith("<#") and text.endswith(">"):
        text = text[2:-1]
    elif text.startswith("<@&") and text.endswith(">"):
        text = text[3:-1]
    return int(text) if text.isdigit() else None


def parse_color(value: Any, fallback: int = 0x5865F2) -> int:
    text = str(value or "").strip().lstrip("#")
    if len(text) != 6:
        return fallback
    try:
        return int(text, 16)
    except ValueError:
        return fallback


def render_template(text: str, **values: Any) -> str:
    rendered = text
    for key, value in values.items():
        rendered = rendered.replace("{" + key + "}", str(value))
    return rendered

