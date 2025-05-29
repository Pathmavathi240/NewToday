import os
import asyncio
import threading
from flask import Flask
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import yt_dlp

# Create downloads directory if it doesn't exist
os.makedirs("downloads", exist_ok=True)

# Flask app for health check
flask_app = Flask(__name__)

@flask_app.route("/")
def health():
    return "Bot is running!"

# Telegram command handler
async def play(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = ' '.join(context.args)

    if not query:
        await update.message.reply_text("தயவுசெய்து தேடல் சொல் அல்லது YouTube இணைப்பு கொடுக்கவும்.")
        return

    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': 'downloads/%(title)s.%(ext)s',
    }

    if not query.startswith("http"):
        query = f"ytsearch:{query}"

    await update.message.reply_text("பதிவிறக்கம் நடக்கிறது...")

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(query, download=True)
            title = info.get('title', 'தெரியாதது')
            await update.message.reply_text(f"பதிவிறக்கம் முடிந்தது: {title}")
    except Exception as e:
        await update.message.reply_text(f"பிழை: {e}")

# Telegram bot startup
async def run_bot():
    token = os.getenv("BOT_TOKEN")
    if not token:
        print("BOT_TOKEN environment variable missing.")
        return

    app = ApplicationBuilder().token(token).build()
    app.add_handler(CommandHandler("play", play))

    try:
        await app.initialize()
        await app.start()
        print("Bot started...")
        await app.updater.start_polling()
    except asyncio.CancelledError:
        print("Shutdown signal received. Cleaning up...")
        await app.updater.stop()
        await app.stop()
        await app.shutdown()

# Entry point
def start():
    # Start Flask in background
    threading.Thread(
        target=lambda: flask_app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080))),
        daemon=True
    ).start()

    # Start bot in main async loop
    asyncio.run(run_bot())

if __name__ == "__main__":
    start()
