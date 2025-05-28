import os
from flask import Flask
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import yt_dlp
import asyncio

# --- Flask app for Koyeb health check ---
flask_app = Flask(__name__)

@flask_app.route("/")
def health():
    return "Bot is running"

# --- Telegram Bot Handler ---
async def play(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = ' '.join(context.args)
    
    if not query:
        await update.message.reply_text("Please provide a search term or YouTube link.")
        return

    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': 'downloads/%(title)s.%(ext)s',
        # Uncomment this line and add cookies.txt if login is needed
        # 'cookiefile': 'cookies.txt',
    }

    # Use ytsearch if plain text is given
    if not query.startswith("http"):
        query = f"ytsearch:{query}"

    await update.message.reply_text("Downloading...")

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(query, download=True)
            title = info.get('title', 'Unknown')
            await update.message.reply_text(f"Downloaded: {title}")
    except Exception as e:
        await update.message.reply_text(f"Failed to download: {str(e)}")

# --- Main Entry Point ---
async def main():
    token = os.getenv("BOT_TOKEN")
    if not token:
        print("BOT_TOKEN is missing in environment variables.")
        return

    application = ApplicationBuilder().token(token).build()
    application.add_handler(CommandHandler("play", play))
    await application.run_polling()

if __name__ == "__main__":
    import threading
    import sys

    # Start Flask server in a thread
    threading.Thread(target=lambda: flask_app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080))), daemon=True).start()

    # Run Telegram bot
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        sys.exit(0)
