import os
import logging
import yt_dlp
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ContextTypes, filters
)

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = os.getenv("BOT_TOKEN")

# Create the bot application
telegram_app = ApplicationBuilder().token(TOKEN).build()

# /start handler
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🎵 Send me the name of a song, and I'll fetch it from YouTube!")

# Message handler for music search
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

# Register handlers
telegram_app.add_handler(CommandHandler("start", start))
telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, search_music))

# Main entry
async def main():
    # Delete the existing webhook to use polling
    await telegram_app.bot.delete_webhook(drop_pending_updates=True)
    # Start polling
    await telegram_app.run_polling()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
