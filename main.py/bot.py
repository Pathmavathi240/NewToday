import os
import logging
import yt_dlp
from flask import Flask, request
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ContextTypes, filters
)

import asyncio

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = os.getenv("BOT_TOKEN")
PORT = int(os.getenv("PORT", "8080"))
APP_URL = os.getenv("APP_URL")  # https://your-koyeb-app.koyeb.app

app = Flask(__name__)
telegram_app = ApplicationBuilder().token(TOKEN).build()

# /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🎵 Send me the name of a song, and I'll fetch it from YouTube!")

# Music search handler
async def search_music(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.message.text
    msg = await update.message.reply_text("🔍 Searching...")

    try:
        ydl_opts = {
            "format": "bestaudio/best",
            "noplaylist": True,
            "quiet": True,
            "outtmpl": "downloads/%(title)s.%(ext)s",
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }],
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(f"ytsearch:{query}", download=False)["entries"][0]
            title = info["title"]
            url = info["webpage_url"]
            await msg.edit_text(f"🎷 Downloading: {title}")
            ydl.download([url])
            file_path = ydl.prepare_filename(info).replace(".webm", ".mp3").replace(".m4a", ".mp3")

        await update.message.reply_audio(audio=open(file_path, "rb"), title=title)
        os.remove(file_path)

    except Exception as e:
        logger.error(e)
        await msg.edit_text("❌ Failed to fetch audio. Try again.")

# Telegram Handlers
telegram_app.add_handler(CommandHandler("start", start))
telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, search_music))

# Flask Webhook Route
@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), telegram_app.bot)
    telegram_app.update_queue.put_nowait(update)
    return "ok"

@app.route("/")
def index():
    return "Bot is alive!"

# Main Async Function
async def main():
    await telegram_app.bot.set_webhook(f"{APP_URL}/{TOKEN}")
    print("✅ Webhook set")
    # Flask run in a thread
    loop = asyncio.get_event_loop()
    from threading import Thread
    Thread(target=lambda: app.run(host="0.0.0.0", port=PORT)).start()
    await telegram_app.initialize()
    await telegram_app.start()
    await telegram_app.updater.start_polling()
    await telegram_app.updater.idle()

# Start everything
if __name__ == "__main__":
    asyncio.run(main())
