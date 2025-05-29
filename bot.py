import os
import asyncio
import threading
from flask import Flask
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import yt_dlp
import nest_asyncio

# Patch nested event loop support
nest_asyncio.apply()

# Create downloads directory
os.makedirs("downloads", exist_ok=True)

# Flask app for Koyeb health checks
flask_app = Flask(__name__)

@flask_app.route("/")
def health():
    return "Bot is running!"

# Telegram /play command
async def play(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = ' '.join(context.args)

    if not query:
        await update.message.reply_text("தயவுசெய்து தேடல் சொல் அல்லது YouTube இணைப்பு கொடுக்கவும்.")
        return

    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': 'downloads/%(title)s.%(ext)s',
        'noplaylist': True,
        'quiet': True
    }

    if not query.startswith("http"):
        query = f"ytsearch:{query}"

    await update.message.reply_text("🎵 பாடல் பதிவிறக்கம் நடக்கிறது...")

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(query, download=True)
            file_path = ydl.prepare_filename(info)
            title = info.get("title", "Unknown")
            duration = info.get("duration", 0)

        await update.message.reply_audio(
            audio=open(file_path, 'rb'),
            title=title,
            duration=duration
        )
    except Exception as e:
        await update.message.reply_text(f"⚠️ பிழை: {str(e)}")

# Telegram bot startup
async def run_bot():
    token = os.getenv("BOT_TOKEN")
    if not token:
        print("❌ BOT_TOKEN environment variable not set.")
        return

    app = ApplicationBuilder().token(token).build()
    app.add_handler(CommandHandler("play", play))

    print("✅ Telegram bot started.")
    await app.run_polling()

# Entry point
def start():
    # Start Flask server for health check
    threading.Thread(
        target=lambda: flask_app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080))),
        daemon=True
    ).start()

    # Reuse existing loop
    loop = asyncio.get_event_loop()
    loop.create_task(run_bot())
    loop.run_forever()

if __name__ == "__main__":
    start()
