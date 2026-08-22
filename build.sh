#!/usr/bin/env bash
set -e

# Python dependencies
pip install -r requirements.txt

# FFmpeg for audio playback
apt-get update -qq
apt-get install -y -qq ffmpeg

# Deno — required by yt-dlp for YouTube JS extraction
curl -fsSL https://deno.land/install.sh | sh
export DENO_INSTALL="$HOME/.deno"
export PATH="$DENO_INSTALL/bin:$PATH"
echo "Deno installed: $(deno --version | head -1)"
