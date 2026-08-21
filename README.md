# General Discord Bot

A clean Python Discord bot with moderation and basic music support. It is intentionally simple so you can add special features gradually.

## Features

- Slash commands
- Prefix commands with `!`
- Moderation: purge, timeout, untimeout, kick, ban, unban
- Music: join, play, pause, resume, skip, stop, queue, leave
- Web dashboard for configuring welcome messages and role requests
- Welcome messages with configurable channel, text, image, thumbnail, and color
- Role request panel with a configurable button and Discord modal form
- Basic utility commands: ping and about

## Setup

1. Install Python 3.10 or newer.
2. Install FFmpeg and make sure `ffmpeg` is available in your terminal.
3. Create a Discord bot at the Discord Developer Portal.
4. Enable these bot settings:
   - Server Members Intent
   - Message Content Intent
5. Invite the bot with these scopes:
   - `bot`
   - `applications.commands`
6. Install dependencies:

```bash
pip install -r requirements.txt
```

7. Copy `.env.example` to `.env`, then put your token in `.env`.
8. Start the bot:

```bash
python bot.py
```

The dashboard starts automatically when the bot starts.

## Dashboard

The local configuration website starts automatically with:

```bash
python bot.py
```

Then open:

```text
http://127.0.0.1:8765
```

If that port is taken or blocked, the dashboard prints the exact URL it started on. You can also choose a port manually:

```bash
DASHBOARD_PORT=9000 python dashboard.py
```

To run only the dashboard without the bot:

```bash
python dashboard.py
```

To disable the automatic dashboard:

```env
DASHBOARD_ENABLED=false
```

The dashboard saves settings to `data/config.json`.

You can configure:

- Welcome message channel, title, message, image, thumbnail, and embed color
- Role request panel channel
- Role request submission channel
- Role to ping when a request is submitted
- Role being requested
- Role request panel text, image, thumbnail, button label, and form fields

Discord IDs should be raw IDs like `123456789012345678`. To copy IDs, enable Developer Mode in Discord, then right-click a channel or role and choose `Copy ID`.

After configuring the role request feature, run this command in Discord:

```text
/role_request_panel
```

That posts the configured role request embed and button. When someone clicks the button, the bot opens the configured form and sends the submission to your configured submission channel.

## Notes

Music uses `yt-dlp` plus FFmpeg. For YouTube and other sites, playback can occasionally break when those sites change their systems. Updating `yt-dlp` usually fixes that:

```bash
pip install -U yt-dlp
```

## Project Layout

```text
bot.py
config.py
cogs/
  general.py
  moderation.py
  music.py
  role_request.py
  welcome.py
web/
  index.html
  styles.css
  app.js
dashboard.py
bot_config.py
data/
  config.json
```
