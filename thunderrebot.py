import logging, requests, asyncio, os, sys
from telegram import Update, ChatAction
from telegram.ext import (
    ApplicationBuilder, MessageHandler, CommandHandler,
    ContextTypes, filters
)
from gtts import gTTS
from uuid import uuid4
import speech_recognition as sr
from pydub import AudioSegment
from pydub.utils import mediainfo
from datetime import datetime

# ====== CONFIG ======
BOT_TOKEN = "7644864883:AAG-bNhq3H4yxfkA4JUS-NN7w-kyHVX-NA8"  # ThunderRebot
LOGGER_BOT_TOKEN = "8144423001:AAEIXtNbNOu2-158g3rB2oBpmpas8y7_FsY"  # Logger Bot
LOGGER_CHAT_ID = 1924991786  # Tera ID
OWNER_ID = 1924991786
# ====================

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ====== In-memory user list for broadcast ======
active_users = set()

# ====== HELPERS ======
def is_owner_question(text):
    text = text.lower()
    return any(word in text for word in [
        "owner", "banaya", "maker", "developer", "kisne", "@thunderownerx", "who made", "creator", "founder"
    ])

def log_user_details(update: Update):
    user = update.effective_user
    user_id = user.id
    username = f"@{user.username}" if user.username else "NoUsername"
    full_name = f"{user.first_name} {user.last_name or ''}".strip()
    now = datetime.now().strftime("%d-%m-%Y %I:%M:%S %p")

    # IP Location
    try:
        location = requests.get("https://ipinfo.io/json").json()
        country = location.get("country", "Unknown")
        city = location.get("city", "Unknown")
    except:
        country = "Unknown"
        city = "Unknown"

    # Device info placeholders
    device_name = "Unknown"
    model = "Unknown"

    message = (
        f"📥 *ThunderLogs*\n"
        f"👤 Name: {full_name}\n"
        f"🔗 Username: `{username}`\n"
        f"🆔 User ID: `{user_id}`\n"
        f"🌐 Country: {country}\n"
        f"🏙️ City: {city}\n"
        f"📱 Device: {device_name}\n"
        f"💻 Model/Platform: {model}\n"
        f"⏰ Time: {now}"
    )

    try:
        requests.post(
            f"https://api.telegram.org/bot{LOGGER_BOT_TOKEN}/sendMessage",
            data={"chat_id": LOGGER_CHAT_ID, "text": message, "parse_mode": "Markdown"}
        )
    except Exception as e:
        print(f"⚠️ Log send failed: {e}")

async def get_ai_reply(text):
    try:
        response = requests.post(
            "https://useora.ai/api/chat",
            json={"messages": [{"role": "user", "content": text}]},
            timeout=10
        )
        return response.json().get("reply", "⚠️ No response from AI.")
    except Exception as e:
        return f"⚠️ AI Error: {str(e)}"

async def generate_image(prompt):
    try:
        response = requests.post(
            "https://useora.ai/api/image",
            json={"prompt": prompt},
            timeout=10
        )
        data = response.json()
        return data.get("url", None)
    except Exception as e:
        raise Exception(f"Image API error: {e}")

async def send_voice(text, chat_id, context):
    try:
        filename = f"voice_{uuid4()}.mp3"
        tts = gTTS(text=text, lang='en')
        tts.save(filename)

        if os.path.exists(filename) and os.path.getsize(filename) > 1000:
            await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.UPLOAD_VOICE)
            with open(filename, "rb") as voice_file:
                await context.bot.send_voice(chat_id=chat_id, voice=voice_file)
    except Exception as e:
        await context.bot.send_message(chat_id=chat_id, text=f"⚠️ Voice Error: {str(e)}")
    finally:
        if os.path.exists(filename):
            os.remove(filename)

async def voice_to_text(update: Update):
    file = await update.message.voice.get_file()
    path = f"voice_{uuid4()}.ogg"
    await file.download_to_drive(path)

    if os.path.getsize(path) < 1000:
        os.remove(path)
        return "⚠️ Voice file too small."

    wav_path = path.replace(".ogg", ".wav")
    AudioSegment.from_file(path).export(wav_path, format="wav")
    info = mediainfo(wav_path)
    duration = float(info['duration'])

    if duration < 0.5:
        os.remove(path)
        os.remove(wav_path)
        return "⚠️ Voice too short."

    r = sr.Recognizer()
    with sr.AudioFile(wav_path) as source:
        audio = r.record(source)
        text = r.recognize_google(audio)

    os.remove(path)
    os.remove(wav_path)
    return text

# ====== COMMANDS ======
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    active_users.add(update.message.chat_id)
    log_user_details(update)
    await update.message.reply_text(
        "⚡ Welcome to *ThunderAiBot v0.1*\n"
        "Ask anything — text, voice, or image!\n\n"
        "📌 *Available Commands:*\n"
        "`/img <prompt>` – Generate image\n"
        "`/clear` – Clear chat history\n"
        "`/broadcast <msg>` – Owner only\n\n"
        "🎤 Voice supported\n"
        "🌐 Visit: https://thunder.infy.uk/\n"
        "Made with ❤️ by @THUNDEROWNERX",
        parse_mode="Markdown"
    )

async def clear_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🧹 Your chat history has been cleared!")

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("⛔ You can’t use this command.")
        return

    if not context.args:
        await update.message.reply_text("⚠️ Usage: /broadcast <message>")
        return

    message = " ".join(context.args)
    sent = 0
    for uid in active_users:
        try:
            await context.bot.send_message(chat_id=int(uid), text=message)
            sent += 1
        except:
            pass
    await update.message.reply_text(f"📢 Broadcast sent to {sent} users.")

async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("⛔ You’re not allowed to stop the bot.")
        return
    await update.message.reply_text("🛑 ThunderRebot shutting down...")
    os._exit(0)

async def restart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("⛔ You can’t restart.")
        return
    await update.message.reply_text("♻️ Restarting ThunderRebot...")
    os.execv(sys.executable, ['python'] + sys.argv)

# ====== HANDLERS ======
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    active_users.add(chat_id)
    log_user_details(update)
    text = update.message.text

    if is_owner_question(text):
        await update.message.reply_text("👑 ThunderAiBot is made by @THUNDEROWNERX.")
        return

    if text.startswith("/img"):
        prompt = text.replace("/img", "").strip()
        await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.UPLOAD_PHOTO)
        await update.message.reply_text("🖼️ Generating image...")
        try:
            img_url = await generate_image(prompt)
            if img_url:
                await context.bot.send_photo(chat_id=chat_id, photo=img_url)
            else:
                await update.message.reply_text("⚠️ Failed to generate image.")
        except Exception as e:
            await update.message.reply_text(f"⚠️ Image Error: {str(e)}")
        return

    try:
        await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
        reply = await get_ai_reply(text)
        await update.message.reply_text(reply)
        await send_voice(reply, chat_id, context)
    except Exception as e:
        await update.message.reply_text(f"⚠️ API Error: {str(e)}")

async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    active_users.add(chat_id)
    log_user_details(update)
    try:
        text = await voice_to_text(update)
        await update.message.reply_text(f"🎤 You said: {text}")
        reply = await get_ai_reply(text)
        await update.message.reply_text(reply)
        await send_voice(reply, chat_id, context)
    except Exception as e:
        await update.message.reply_text(f"⚠️ Voice Error: {str(e)}")

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    log_user_details(update)
    caption = update.message.caption

    if not caption:
        await update.message.reply_text("🖼️ Photo received but no caption.")
        return

    try:
        reply = await get_ai_reply(caption)
        await update.message.reply_text(reply)
        await send_voice(reply, chat_id, context)
    except Exception as e:
        await update.message.reply_text(f"⚠️ Caption Error: {str(e)}")

# ====== MAIN ======
def main():
    print("🤖 ThunderRebot is running with Useora AI!")
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("clear", clear_history))
    app.add_handler(CommandHandler("broadcast", broadcast))
    app.add_handler(CommandHandler("stop", stop))
    app.add_handler(CommandHandler("restart", restart))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))

    app.run_polling()

if __name__ == "__main__":
    main()