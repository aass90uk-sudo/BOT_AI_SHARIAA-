import os
import logging
import threading
import random
from http.server import BaseHTTPRequestHandler, HTTPServer
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from groq import Groq

# إعداد السجلات (Logs)
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# جلب المتغيرات البيئية
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
CHANNEL_CHAT_ID = os.getenv("CHANNEL_CHAT_ID")

if not TELEGRAM_TOKEN or not GROQ_API_KEY:
    logger.error("خطأ: لم يتم ضبط المتغيرات البيئية TELEGRAM_TOKEN أو GROQ_API_KEY!")
    exit(1)

# تهيئة Groq
groq_client = Groq(api_key=GROQ_API_KEY)
FOOTER_TEXT = "\n\n🖤 صدقة جارية للأخت «الأندلسية» غفر الله لها 🖤"

# قائمة التفاعلات
REACTION_EMOJIS = ["😘", "🥰", "❤️", "🕊️", "🐳"]

# ----------------- سيرفر الفحص لمنصة Railway -----------------
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(b"Bot is running successfully!")

def start_health_server():
    try:
        port = int(os.environ.get("PORT", 8080))
        server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
        logger.info(f"تم تشغيل سيرفر الفحص على المنفذ: {port}")
        server.serve_forever()
    except Exception as e:
        logger.error(f"خطأ في سيرفر الفحص: {e}")
# -----------------------------------------------------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """أمر البدء"""
    await update.message.reply_text(
        "مرحباً بكم في البوت الدعوي المتكامل.\n"
        "المشروع يعمل كصدقة جارية للأخت «الأندلسية» غفر الله لها ولنا وللمسلمين."
    )

def generate_ai_content(prompt: str, system_role: str, is_group_reply: bool = False) -> str:
    try:
        completion = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system_role},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=800
        )
        reply_content = completion.choices[0].message.content
        if not is_group_reply:
            reply_content += FOOTER_TEXT
        return reply_content
    except Exception as e:
        logger.error(f"خطأ أثناء توليد النص من Groq: {e}")
        return "حدث خطأ أثناء معالجة الطلب، نسأل الله التيسير والسداد."

async def auto_post_job(context: ContextTypes.DEFAULT_TYPE):
    if not CHANNEL_CHAT_ID:
        logger.warning("تنبيه: لم يتم ضبط CHANNEL_CHAT_ID!")
        return
        
    logger.info("بدء توليد ونشر الموعظة الدورية...")
    system_role = "أنت خطيب وموجه إيماني بليغ، تتقن الكتابة الحماسية المؤثرة والدعوية المستندة إلى الوحيين."
    prompt = (
        "اكتب موعظة إيمانية حماسية بليغة ومؤثرة جداً للأمة الإسلامية. "
        "ركز على عقيدة الولاء والبراء، ثبات الأمة، والدعاء للمسلمين في كل بقاع الأرض."
    )
    content = generate_ai_content(prompt=prompt, system_role=system_role, is_group_reply=False)
    
    try:
        await context.bot.send_message(chat_id=CHANNEL_CHAT_ID, text=content)
        logger.info("تم نشر الموعظة الدورية بنجاح.")
    except Exception as e:
        logger.error(f"فشل إرسال الرسالة إلى القناة: {e}")

# ----------------- معالج منشورات القناة (تفاعل فقط) -----------------
async def handle_channel_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    post = update.channel_post
    if not post:
        return

    try:
        chosen_emoji = random.choice(REACTION_EMOJIS)
        await context.bot.set_message_reaction(
            chat_id=post.chat.id,
            message_id=post.message_id,
            reaction=[{"type": "emoji", "emoji": chosen_emoji}],
            is_big=False
        )
        logger.info(f"تم وضع تفاعل {chosen_emoji} على منشور القناة.")
    except Exception as e:
        logger.error(f"فشل وضع التفاعل على منشور القناة: {e}")

# ----------------- معالج المجموعات والرسائل -----------------
async def handle_group_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    if not message or not message.text:
        return

    chat_type = update.effective_chat.type

    # وضع تفاعل عشوائي برمجياً
    try:
        chosen_emoji = random.choice(REACTION_EMOJIS)
        await context.bot.set_message_reaction(
            chat_id=update.effective_chat.id,
            message_id=message.message_id,
            reaction=[{"type": "emoji", "emoji": chosen_emoji}],
            is_big=False
        )
    except Exception as e:
        logger.error(f"فشل وضع التفاعل: {e}")

    # الرد الآلي بالذكاء الاصطناعي
    bot_username = context.bot.username
    is_mentioned = f"@{bot_username}" in message.text if bot_username else False
    is_reply_to_bot = message.reply_to_message and message.reply_to_message.from_user.id == context.bot.id
    is_private = chat_type == "private"

    if is_mentioned or is_reply_to_bot or is_private:
        user_query = message.text.replace(f"@{bot_username}", "").strip() if bot_username else message.text
        if not user_query:
            user_query = "مرحباً بك"

        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
        
        system_role = (
            "أنت مجيب وموجه شرعي وفكري ذكي جداً، تخاطب الإخوة والأخوات الموحدين. "
            "أجوبتك مبنية على العقيدة الإسلامية الصحيحة. "
            "لا تكتب إيموجيات أو كلمة 'تفاعل:' كجزء من النص إطلاقاً."
        )
        
        ai_reply = generate_ai_content(prompt=user_query, system_role=system_role, is_group_reply=True)
        
        try:
            await message.reply_text(text=ai_reply)
        except Exception as e:
            logger.error(f"فشل إرسال الرد: {e}")

def main():
    # تشغيل سيرفر الفحص
    threading.Thread(target=start_health_server, daemon=True).start()

    # بناء التطبيق
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.ChatType.CHANNEL, handle_channel_post))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_group_message))

    # تجنب انهيار البوت في حال عدم تثبيت APScheduler
    if application.job_queue:
        try:
            application.job_queue.run_repeating(auto_post_job, interval=1800, first=10)
            logger.info("تم تفعيل جدول المهام بنجاح.")
        except Exception as e:
            logger.error(f"فشل تفعيل JobQueue: {e}")
    else:
        logger.warning("تنبيه: JobQueue غير مفعل، يرجى إضافة python-telegram-bot[job-queue] في requirements.txt")

    logger.info("البوت يعمل الآن...")
    application.run_polling(close_loop=False, allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
            
