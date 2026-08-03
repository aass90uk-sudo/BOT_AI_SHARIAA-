import os
import logging
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from google import genai
from google.genai import types
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# إعداد السجلات (Logs) لمتابعة أداء البوت على Railway
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# جلب مفاتيح التشغيل السرية من بيئة النظام (Railway)
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
CHANNEL_CHAT_ID = os.getenv("CHANNEL_CHAT_ID")

# التحقق من وجود المتغيرات الأساسية
if not TELEGRAM_TOKEN or not GEMINI_API_KEY:
    logger.error("خطأ: لم يتم ضبط المتغيرات البيئية TELEGRAM_TOKEN أو GEMINI_API_KEY!")
    exit(1)

# تهيئة عميل Gemini؛ المفتاح لا يُحفظ في الكود أو المستودع
gemini_client = genai.Client(api_key=GEMINI_API_KEY)
GEMINI_MODEL = "gemini-3-flash-preview"
FOOTER_TEXT = "\n\n🖤 صدقة جارية للأخت «الأندلسية» غفر الله لها 🖤"

# ----------------- سيرفر وهمي لإرضاء منصة Railway -----------------
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(b"Bot is running inside Railway successfully!")

    def log_message(self, format, *args):
        pass  # كتم سجلات الطلبات الوهمية

def start_health_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
    logger.info(f"تم تشغيل سيرفر الفحص الوهمي على المنفذ: {port}")
    server.serve_forever()
# -----------------------------------------------------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """أمر البدء للبوت"""
    await update.message.reply_text(
        "مرحباً بكم في البوت الدعوي المتكامل.\n"
        "المشروع يعمل كصدقة جارية للأخت «الأندلسية» غفر الله لها ولنا وللمسلمين."
    )

async def generate_ai_content(prompt: str, system_role: str, is_group_reply: bool = False) -> str:
    try:
        response = await gemini_client.aio.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_role,
                temperature=0.7,
                max_output_tokens=8192,
            ),
        )
        reply_content = (response.text or "").strip()
        if not reply_content:
            logger.warning("أعاد Gemini استجابة فارغة.")
            return "لم أتمكن من صياغة رد الآن، يرجى المحاولة مرة أخرى."

        if not is_group_reply:
            reply_content += FOOTER_TEXT
        return reply_content
    except Exception as e:
        status_code = getattr(e, "status_code", None)
        if status_code == 429 or "429" in str(e):
            logger.error("تجاوز حد استخدام Gemini: %s", e)
            return "عذراً، وصل البوت لحد الاستخدام المتاح. يرجى المحاولة لاحقاً بإذن الله."

        logger.error(f"خطأ أثناء توليد النص من Gemini: {e}")
        return "حدث خطأ أثناء معالجة الطلب، نسأل الله التيسير والسداد."

async def auto_post_job(context: ContextTypes.DEFAULT_TYPE):
    if not CHANNEL_CHAT_ID:
        logger.warning("تنبيه: لم يتم ضبط CHANNEL_CHAT_ID!")
        return

    logger.info("بدء توليد ونشر الموعظة الدورية في القناة...")
    system_role = "أنت خطيب وموجه إيماني بليغ، تتقن الكتابة الحماسية المؤثرة والدعوية المستندة إلى الوحيين والوعي بواقع الأمة."
    prompt = (
        "اكتب موعظة إيمانية حماسية بليغة ومؤثرة جداً للأمة الإسلامية. "
        "ركز على عقيدة الولاء والبراء، ثبات الأمة، فضل الجهاد والرباط، "
        "مراغمة الكفار في جزيرة العرب، والدعاء لأبطال وثغور المسلمين في كل بقاع الأرض ،مع وضع نصائح قيمة للإخوة المناصرين وعدم كشف الاسرار بداخل المجموعات العامة وأنصحهم بأن يأخدو حِذرهم من المتربصين في منصات التواصل."
    )
    content = await generate_ai_content(prompt=prompt, system_role=system_role, is_group_reply=False)

    try:
        await context.bot.send_message(chat_id=CHANNEL_CHAT_ID, text=content)
        logger.info("تم نشر الموعظة الدورية بنجاح.")
    except Exception as e:
        logger.error(f"فشل إرسال الرسالة إلى القناة: {e}")

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error(f"خطأ غير معالج: {context.error}", exc_info=context.error)

async def handle_channel_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """يرد على كل منشور جديد في القناة مباشرةً (احتياطي)"""
    post = update.channel_post
    if not post or not post.text:
        return

    logger.info(f"منشور جديد في القناة: {post.chat.title}")
    system_role = (
        "أنت معلّق إيماني بليغ، تكتب تعليقاً موجزاً ومؤثراً على منشور إسلامي دعوي. "
        "تعليقك يعمّق المعنى ويزيد الفائدة ويحرّك القلوب. اجعله قصيراً لا يتجاوز سطرين أو ثلاثة."
    )
    prompt = f"اكتب تعليقاً إيمانياً موجزاً ومؤثراً على هذا المنشور:\n\n{post.text}"

    ai_comment = await generate_ai_content(prompt=prompt, system_role=system_role, is_group_reply=False)

    try:
        await context.bot.send_message(
            chat_id=post.chat_id,
            text=ai_comment,
            reply_to_message_id=post.message_id
        )
        logger.info("تم إرسال التعليق على المنشور بنجاح.")
    except Exception as e:
        logger.error(f"فشل إرسال التعليق على منشور القناة: {e}")

async def handle_discussion_forward(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    يرد في المجموعة المرتبطة عندما يُعاد توجيه منشور القناة إليها تلقائياً.
    Telegram يرسل is_automatic_forward=True لهذه الرسائل.
    """
    message = update.effective_message
    if not message or not message.text:
        return

    logger.info(f"منشور محوَّل تلقائياً من القناة إلى المجموعة: {message.chat.title}")
    system_role = (
        "أنت معلّق إيماني بليغ، تكتب تعليقاً موجزاً ومؤثراً على منشور إسلامي دعوي. "
        "تعليقك يعمّق المعنى ويزيد الفائدة ويحرّك القلوب. اجعله قصيراً لا يتجاوز سطرين أو ثلاثة."
    )
    prompt = f"اكتب تعليقاً إيمانياً موجزاً ومؤثراً على هذا المنشور:\n\n{message.text}"

    ai_comment = await generate_ai_content(prompt=prompt, system_role=system_role, is_group_reply=False)

    try:
        await message.reply_text(text=ai_comment)
        logger.info("تم إرسال التعليق في المجموعة المرتبطة بنجاح.")
    except Exception as e:
        logger.error(f"فشل إرسال التعليق في المجموعة المرتبطة: {e}")

async def handle_group_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    if not message or not message.text:
        return

    bot_username = context.bot.username
    is_mentioned = f"@{bot_username}" in message.text
    is_reply_to_bot = message.reply_to_message and message.reply_to_message.from_user.id == context.bot.id
    is_private = update.effective_chat.type == "private"

    if is_mentioned or is_reply_to_bot or is_private:
        user_query = message.text.replace(f"@{bot_username}", "").strip()
        if not user_query:
            user_query = "مرحباً بك"

        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
        system_role = (
            "أنت مجيب وموجه شرعي وفكري ذكي جداً، تخاطب الإخوة والأخوات الموحدين في مجموعة نقاش دعوية وثقافية. "
            "أجوبتك مبنية على العقيدة الإسلامية الصحيحة والولاء والبراء ونصرة قضايا المسلمين."
        )
        ai_reply = await generate_ai_content(prompt=user_query, system_role=system_role, is_group_reply=True)

        try:
            await message.reply_text(text=ai_reply)
        except Exception as e:
            logger.error(f"فشل إرسال الرد: {e}")

def main():
    # تشغيل السيرفر الوهمي في مسار منفصل (Thread) حتى لا يعطل البوت
    threading.Thread(target=start_health_server, daemon=True).start()

    # تشغيل البوت
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    # منشورات القناة المُعاد توجيهها تلقائياً إلى المجموعة المرتبطة (التعليقات)
    application.add_handler(MessageHandler(filters.IS_AUTOMATIC_FORWARD & filters.TEXT, handle_discussion_forward))
    # رسائل المجموعة العادية والخاصة
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & ~filters.IS_AUTOMATIC_FORWARD, handle_group_message))
    # منشورات القناة المباشرة (احتياطي)
    application.add_handler(MessageHandler(filters.UpdateType.CHANNEL_POSTS & filters.TEXT, handle_channel_post))
    application.add_error_handler(error_handler)

    job_queue = application.job_queue
    if job_queue:
        job_queue.run_repeating(auto_post_job, interval=10800, first=60)  # كل 3 ساعات بدل 30 دقيقة
        logger.info("تم تفعيل مجدول المهام الدوري.")

    logger.info("البوت يبدأ الاستماع الآن...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
