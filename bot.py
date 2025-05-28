import os
import asyncio
import threading
from flask import Flask
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import yt_dlp

flask_app = Flask(__name__)

@flask_app.route("/")
def health():
    return "Bot is running!"

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

async def start_bot():
    token = os.getenv("BOT_TOKEN")
    if not token:
        print("BOT_TOKEN என்விரோன்மெண்ட் வெரியபிள் இல்லை.")
        return

    app = ApplicationBuilder().token(token).build()
    app.add_handler(CommandHandler("play", play))

    await app.run_polling()  # ✅ புதிய மற்றும் சரியான method

if __name__ == "__main__":
    # Flask ஹெல்த் செக்
    threading.Thread(
        target=lambda: flask_app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080))),
        daemon=True
    ).start()

    # Telegram bot ஆரம்பிக்கவும்
    loop = asyncio.get_event_loop()
    loop.create_task(start_bot())
    loop.run_forever()
