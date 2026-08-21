#!/usr/bin/env bash
set -e

# Install Python dependencies
pip install -r requirements.txt

# Install FFmpeg (required for music playback)
apt-get update -qq
apt-get install -y -qq ffmpeg
