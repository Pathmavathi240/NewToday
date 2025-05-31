from flask import Flask
import threading
import asyncio
import os
from datetime import timedelta
from urllib.parse import urlparse
from pyrogram import Client, filters, idle
from pyrogram.types import Message
from youtube_dl import YoutubeDL
from PIL import Image
import ffmpeg

# --- Flask App for Koyeb Health Check ---
app = Flask(__name__)

@app.route('/')
def home():
    return "✅ Telegram Music Bot is running!"

# --- Telegram Bot Logic Starts Here ---
MUSIC_MAX_LENGTH = 10800
DELAY_DELETE_INFORM = 10
TG_THUMB_MAX_LENGTH = 320
REGEX_SITES = (
    r"^((?:https?:)?\/\/)"
    r"?((?:www|m)\.)"
    r"?((?:youtube\.com|youtu\.be|soundcloud\.com|mixcloud\.com))"
    r"(\/)([-a-zA-Z0-9()@:%_\+.~#?&//=]*)([\w\-]+)(\S+)?$"
)
REGEX_EXCLUDE_URL = (
    r"\/channel\/|\/playlist\?list=|&list=|\/sets\/"
)

def get_music_chats():
    chats = []
    for x in os.environ["MUSIC_CHATS"].split(" "):
        try:
            chats.append(int(x))
        except ValueError:
            chats.append(x)
    return chats

MUSIC_CHATS = get_music_chats()
API_ID = os.environ["API_ID"]
API_HASH = os.environ["API_HASH"]
BOT_TOKEN = os.environ["BOT_TOKEN"]

bot = Client(
    "tgmusicbot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

main_filter = filters.text & filters.chat(MUSIC_CHATS) & filters.incoming

@bot.on_message(filters.command("start") & (filters.private | filters.chat(MUSIC_CHATS)))
async def start_command(_, message: Message):
    await message.reply_text(
        "👋 Hello! I'm a Telegram Music Bot.\n"
        "Send me a YouTube/SoundCloud/Mixcloud music link "
        "in a supported group or reply to a message to download."
    )

@bot.on_message(main_filter & filters.regex("^/ping$"))
async def ping_pong(_, message):
    await _reply_and_delete_later(message, "pong", DELAY_DELETE_INFORM)

@bot.on_message(main_filter & filters.regex(REGEX_SITES) & ~filters.regex(REGEX_EXCLUDE_URL))
async def music_downloader(_, message: Message):
    await _fetch_and_send_music(message)

async def _fetch_and_send_music(message: Message):
    await message.reply_chat_action("typing")
    try:
        ydl_opts = {
            'format': 'bestaudio',
            'outtmpl': '%(title)s - %(extractor)s-%(id)s.%(ext)s',
            'writethumbnail': True
        }
        ydl = YoutubeDL(ydl_opts)
        info_dict = ydl.extract_info(message.text, download=False)

        if not message.reply_to_message and _youtube_video_not_music(info_dict):
            inform = ("This video is not under Music category, "
                      "you can resend the link as a reply to force download it")
            await _reply_and_delete_later(message, inform, DELAY_DELETE_INFORM)
            return

        if info_dict['duration'] > MUSIC_MAX_LENGTH:
            readable_max_length = str(timedelta(seconds=MUSIC_MAX_LENGTH))
            inform = ("This won't be downloaded because its audio length is "
                      "longer than the limit `{}` which is set by the bot"
                      .format(readable_max_length))
            await _reply_and_delete_later(message, inform, DELAY_DELETE_INFORM)
            return

        d_status = await message.reply_text("Downloading...", quote=True,
                                            disable_notification=True)
        ydl.process_info(info_dict)
        audio_file = ydl.prepare_filename(info_dict)

        task = asyncio.create_task(_upload_audio(message, info_dict, audio_file))

        await message.reply_chat_action("upload_document")
        await d_status.delete()

        while not task.done():
            await asyncio.sleep(4)
            await message.reply_chat_action("upload_document")
        await message.reply_chat_action("cancel")

        if message.chat.type == "private":
            await message.delete()

    except Exception as e:
        await message.reply_text(repr(e))

def _youtube_video_not_music(info_dict):
    return info_dict['extractor'] == 'youtube' and 'Music' not in info_dict.get('categories', [])

async def _reply_and_delete_later(message: Message, text: str, delay: int):
    reply = await message.reply_text(text, quote=True)
    await asyncio.sleep(delay)
    await reply.delete()

async def _upload_audio(message: Message, info_dict, audio_file):
    basename = audio_file.rsplit(".", 1)[-2]
    if info_dict['ext'] == 'webm':
        audio_file_opus = basename + ".opus"
        ffmpeg.input(audio_file).output(audio_file_opus, codec="copy").run()
        os.remove(audio_file)
        audio_file = audio_file_opus

    thumbnail_url = info_dict['thumbnail']
    if os.path.isfile(basename + ".jpg"):
        thumbnail_file = basename + ".jpg"
    else:
        thumbnail_file = basename + "." + _get_file_extension_from_url(thumbnail_url)

    squarethumb_file = basename + "_squarethumb.jpg"
    make_squarethumb(thumbnail_file, squarethumb_file)

    webpage_url = info_dict['webpage_url']
    title = info_dict['title']
    caption = f"<b><a href=\"{webpage_url}\">{title}</a></b>"
    duration = int(float(info_dict['duration']))
    performer = info_dict['uploader']

    await message.reply_audio(audio_file,
                              caption=caption,
                              duration=duration,
                              performer=performer,
                              title=title,
                              parse_mode='HTML',
                              thumb=squarethumb_file)

    for f in (audio_file, thumbnail_file, squarethumb_file):
        os.remove(f)

def _get_file_extension_from_url(url):
    url_path = urlparse(url).path
    basename = os.path.basename(url_path)
    return basename.split(".")[-1]

def make_squarethumb(thumbnail, output):
    original_thumb = Image.open(thumbnail)
    squarethumb = _crop_to_square(original_thumb)
    squarethumb.thumbnail((TG_THUMB_MAX_LENGTH, TG_THUMB_MAX_LENGTH), Image.ANTIALIAS)
    squarethumb.save(output)

def _crop_to_square(img):
    width, height = img.size
    length = min(width, height)
    left = (width - length) / 2
    top = (height - length) / 2
    right = (width + length) / 2
    bottom = (height + length) / 2
    return img.crop((left, top, right, bottom))

# --- Start Bot and Web Server Together ---
def run():
    async def start_bot():
        await bot.start()
        print(">>> BOT STARTED")
        await idle()
        await bot.stop()
        print(">>> BOT STOPPED")

    # Run bot in main thread to avoid signal issues
    asyncio.get_event_loop().create_task(start_bot())

    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

if __name__ == "__main__":
    asyncio.run(bot.start())  # start bot first
    print(">>> BOT STARTED")
    run()
