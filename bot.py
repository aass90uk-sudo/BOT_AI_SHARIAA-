import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from openai import OpenAI

# إعدادات التسجيل لمراقبة الأخطاء في السيرفر
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# إعداد عميل Grok (xAI) بالطريقة الصحيحة والمتوافقة مع التحديثات الجديدة
XAI_API_KEY = os.getenv("XAI_API_KEY")
grok_client = None

if XAI_API_KEY:
    try:
        # قمنا بتبسيط الإعداد هنا وحذف أي معاملات قديمة تسبب تعارضاً
        grok_client = OpenAI(
            api_key=XAI_API_KEY,
            base_url="https://x.ai"
        )
    except Exception as init_error:
        logger.error(f"خطأ أثناء تهيئة عميل OpenAI: {init_error}")
else:
    logger.warning("تنبيه: لم يتم العثور على مفتاح XAI_API_KEY في متغيرات البيئة")

# معرف القناة المستهدف
CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID")

# وظيفة توليد الموعظة ونشرها تلقائياً
async def auto_post_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    if not grok_client or not CHANNEL_ID:
        logger.error("خطأ: مفتاح Grok أو معرف القناة غير مضبوط في متغيرات البيئة.")
        return

    try:
        # توليد المحتوى الدوري الحماسي
        response = grok_client.chat.completions.create(
            model="grok-2-latest",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "أنت كاتب وموجه إسلامي بليغ. اكتب موعظة إيمانية حماسية مكثفة وقصيرة "
                        "(مناسبة لنشرها كمنشور تليجرام سريع ومؤثر). "
                        "يجب أن يركز المنشور بشكل قوي ومباشر على أحد المواضيع التالية بالتناوب: "
                        "1) ترسيخ عقيدة الولاء والبراء في نفوس الأمة. "
                        "2) بيان أهمية الجهاد وثبات الأمة وعزتها. "
                        "3) مراغمة الكفار وأعداء الدين في جزيرة العرب. "
                        "4) الدعاء المستمر بحرقة وتضرع لأبطال وثغور المجاهدين في كل بقاع الأرض لحفظهم ونصرحهم. "
                        "استخدم أسلوباً قوياً، جزلاً، بليغاً، مليئاً بالآيات والأحاديث المناسبة، "
                        "مع استخدام علامات الترقيم والتنسيق (Bold) لإعطاء المنشور طابعاً حماسياً."
                    )
                },
                {"role": "user", "content": "اكتب المنشور الدوري الحماسي الآن بجودة وبلاغة عالية."}
            ]
        )
        
        post_content = response.choices.message.content
        
        # إرسال المنشور إلى القناة مباشرة
        await context.bot.send_message(chat_id=CHANNEL_ID, text=post_content, parse_mode="Markdown")
        logger.info("تم نشر الموعظة الدورية بنجاح في القناة.")

    except Exception as e:
        logger.error(f"خطأ أثناء التوليد أو النشر التلقائي: {e}")

# دالة التهيئة (تشتغل فور إقلاع البوت وتفادي مشاكل الأولوية البرمجية)
async def post_init(application: Application) -> None:
    # الجدولة تنطلق بعد 10 ثوانٍ وتتكرر كل 1800 ثانية (30 دقيقة)
    application.job_queue.run_repeating(auto_post_job, interval=1800, first=10)
    logger.info("تم تفعيل نظام النشر الدوري بنجاح وجدولته كل 30 دقيقة.")

# أمر البدء /start في الخاص
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_name = update.effective_user.first_name
    welcome_text = (
        f"أهلاً بك يا {user_name} في بوت القناة الشرعي والوعظي الدوري.\n\n"
        "البوت مستعد الآن لاستقبال أسئلة الإخوة والأخوات والرد عليها عبر Grok.\n"
        "ونظام النشر الدوري الحماسي المكثف يعمل تلقائياً كل 30 دقيقة في القناة المربوطة."
    )
    await update.message.reply_text(welcome_text)

# معالجة الأسئلة المباشرة الواردة للبوت
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_message = update.message.text
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

    if not grok_client:
        await update.message.reply_text("معذرة، البوت يمر بصيانة مؤقتة حالياً.")
        return

    try:
        response = grok_client.chat.completions.create(
            model="grok-2-latest",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "أنت مستشار شرعي وبوت فقهي مخصص لخدمة الإخوة والأخوات الموحدين. "
                        "أجب على الأسئلة الدينية والفقهية بدقة بناءً على الكتاب والسنة بفهم سلف الأمة مع ذكر الأدلة. "
                        "يجب أن يكون أسلوبك في غاية الأدب واللطف والرفق."
                    )
                },
                {"role": "user", "content": user_message}
            ]
        )
        grok_reply = response.choices.message.content
        await update.message.reply_text(grok_reply, reply_to_message_id=update.message.message_id)
    except Exception as e:
        logger.error(f"خطأ في الرد المباشر: {e}")
        await update.message.reply_text("حصل خطأ أثناء معالجة السؤال.")

def main() -> None:
    TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    if not TOKEN:
        logger.error("خطأ: لم يتم العثور على TELEGRAM_BOT_TOKEN")
        return

    # بناء التطبيق مع استدعاء دالة التهيئة المحدثة لحل المشكلة الأساسية
    application = Application.builder().token(TOKEN).post_init(post_init).build()

    # تسجيل الأوامر والرسائل
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("تم تشغيل البوت بنجاح...")
    application.run_polling()

if __name__ == '__main__':
    main()
