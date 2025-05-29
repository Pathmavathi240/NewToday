#!/bin/bash
python3 web.py &   # Health check server
python3 bot.py     # Telegram bot
