import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from openai import OpenAI

# إعدادات التسجيل لمراقبة الأخطاء
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# إعداد عميل Grok (xAI) باستخدام مكتبة OpenAI المعتمدة لديهم
# سيتم جلب المفتاح تلقائياً من متغيرات البيئة في Railway
XAI_API_KEY = os.getenv("XAI_API_KEY")
grok_client = None

if XAI_API_KEY:
    grok_client = OpenAI(
        api_key=XAI_API_KEY,
        base_url="https://x.ai", # الرابط الرسمي لـ Grok API
    )
else:
    logger.warning("تنبيه: لم يتم العثور على مفتاح XAI_API_KEY. البوت سيعمل بردود افتراضية.")

# أمر البدء /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_name = update.effective_user.first_name
    welcome_text = (
        f"أهلاً بكِ وبكَ يا {user_name} في بوت القناة الشرعي الفقهي.\n\n"
        "نسعد باستقبال أسئلتكم الشرعية. تفضل بكتابة سؤالك الفقهي أو العقدي بكل وضوح، "
        "وسيجيبك البوت مستنداً إلى الأدلة الشرعية بكل رفق ولين إن شاء الله.\n\n"
        "تفضل بطرح سؤالك الآن 👇"
    )
    await update.message.reply_text(welcome_text)

# أمر المساعدة /help
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    help_text = (
        "هذا البوت مدعوم بالذكاء الاصطناعي لخدمة الإخوة والأخوات.\n"
        "• اطرح سؤالك الفقهي مباشرة.\n"
        "• يرجى التزام الأدب والوضوح للحصول على أدق إجابة شرعية."
    )
    await update.message.reply_text(help_text)

# معالجة الأسئلة وإرسالها إلى Grok
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_message = update.message.text
    
    # إشعار المستخدم بأن البوت يكتب الآن
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

    if not grok_client:
        await update.message.reply_text(
            "معذرة، البوت يمر بصيانة مؤقتة حالياً (لم يتم تفعيل مفتاح الذكاء الاصطناعي).",
            reply_to_message_id=update.message.message_id
        )
        return

    try:
        # توجيه Grok (System Prompt) للالتزام بالمنهج الشرعي والأدب الرفيع
        response = grok_client.chat.completions.create(
            model="grok-2-latest", # أو النموذج الذي تفضله مثل grok-2-1212
            messages=[
                {
                    "role": "system",
                    "content": (
                        "أنت مستشار شرعي وبوت فقهي مخصص لخدمة الإخوة والأخوات الموحدين. "
                        "يجب أن تجيب على الأسئلة الدينية والفقهية والعقدية بدقة بالغة بناءً على الكتاب والسنة "
                        "بفهم سلف الأمة، مع ذكر الأدلة الشرعية إن وجدت. "
                        "يجب أن يكون أسلوبك في غاية الأدب، اللطف، الرفق، واللين والترحيب بالمسلمين. "
                        "إذا كان السؤال خارج النطاق الشرعي أو الديني، اعتذر بلطف واطلب التركيز على الأمور الدينية."
                    )
                },
                {"role": "user", "content": user_message}
            ]
        )
        
        # استخراج رد Grok
        grok_reply = response.choices[0].message.content
        
        # إرسال الرد للمستخدم كرقم مرجعي لسؤاله
        await update.message.reply_text(grok_reply, reply_to_message_id=update.message.message_id)

    except Exception as e:
        logger.error(f"خطأ أثناء الاتصال بـ Grok: {e}")
        await update.message.reply_text(
            "حصل خطأ أثناء معالجة السؤال، يرجى المحاولة مرة أخرى لاحقاً أو صياغة السؤال بشكل أبسط.",
            reply_to_message_id=update.message.message_id
        )

def main() -> None:
    TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    
    if not TOKEN:
        logger.error("خطأ: لم يتم العثور على متغير البيئة TELEGRAM_BOT_TOKEN")
        return

    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("تم بدء تشغيل بوت Grok الشرعي...")
    application.run_polling()

if __name__ == '__main__':
    main()
                       
