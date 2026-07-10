import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from groq import Groq

# إعداد السجلات (Logs) لمتابعة أداء البوت على Railway
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# جلب مفاتيح التشغيل السرية من بيئة النظام (Railway)
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
CHANNEL_CHAT_ID = os.getenv("CHANNEL_CHAT_ID")  # معرف القناة العامة (مثال: @my_channel)

# التحقق من وجود المتغيرات الأساسية
if not TELEGRAM_TOKEN or not GROQ_API_KEY:
    logger.error("خطأ: لم يتم ضبط المتغيرات البيئية TELEGRAM_TOKEN أو GROQ_API_KEY!")
    exit(1)

# تهيئة عميل Groq
groq_client = Groq(api_key=GROQ_API_KEY)

# الخاتمة الثابتة كصدقة جارية
FOOTER_TEXT = "\n\n🖤 صدقة جارية للأخت «الأندلسية» غفر الله لها 🖤"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """أمر البدء عند التحدث مع البوت بشكل خاص"""
    await update.message.reply_text(
        "مرحباً بكم في البوت الدعوي المتكامل.\n"
        "المشروع يعمل كصدقة جارية للأخت «الأندلسية» غفر الله لها ولنا وللمسلمين.\n\n"
        "📢 يقوم البوت بالنشر التلقائي في القناة، والرد الذكي على الاستفسارات داخل المجموعة الدينية المربوطة بها."
    )

def generate_ai_content(prompt: str, system_role: str, is_group_reply: bool = False) -> str:
    """دالة مركزية لتوليد النصوص عبر ذكاء Groq الاصطناعي (نموذج llama-3.3-70b-versatile)"""
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
        
        reply_content = completion.choices.message.content
        # إضافة التوقيع (الصدقة الجارية) في منشورات القناة فقط لعدم تكرارها بشكل مزعج في الجروب
        if not is_group_reply:
            reply_content += FOOTER_TEXT
        return reply_content
    except Exception as e:
        logger.error(f"خطأ أثناء توليد النص من Groq: {e}")
        return "حدث خطأ أثناء معالجة الطلب، نسأل الله التيسير والسداد."

async def auto_post_job(context: ContextTypes.DEFAULT_TYPE):
    """الوظيفة الدورية للنشر التلقائي في القناة العامة كل 30 دقيقة"""
    if not CHANNEL_CHAT_ID:
        logger.warning("تنبيه: لم يتم ضبط CHANNEL_CHAT_ID، لن يتم النشر التلقائي في القناة.")
        return
        
    logger.info("بدء توليد ونشر الموعظة الدورية في القناة...")
    
    system_role = "أنت خطيب وموجه إيماني بليغ، تتقن الكتابة الحماسية المؤثرة والدعوية المستندة إلى الوحيين والوعي بواقع الأمة."
    prompt = (
        "اكتب موعظة إيمانية حماسية بليغة ومؤثرة جداً للأمة الإسلامية. "
        "ركز على عقيدة الولاء والبراء، ثبات الأمة، فضل الجهاد والرباط، "
        "مراغمة الكفار في جزيرة العرب، والدعاء لأبطال وثغور المسلمين في كل بقاع الأرض. "
        "اجعل الأسلوب قوياً، رصيناً، ومحفزاً للقلوب، دون أي مقدمات أو هوامش تفاعلية خارج النص."
    )
    
    content = generate_ai_content(prompt=prompt, system_role=system_role, is_group_reply=False)
    
    try:
        await context.bot.send_message(chat_id=CHANNEL_CHAT_ID, text=content)
        logger.info("تم نشر الموعظة الدورية في القناة بنجاح.")
    except Exception as e:
        logger.error(f"فشل إرسال الرسالة إلى القناة: {e}")

async def handle_group_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة الرسائل داخل المجموعات والرد على الإخوة والأخوات بذكاء وعقيدة صحيحة"""
    message = update.effective_message
    
    # التحقق من أن الرسالة نصية وليست فارغة
    if not message.text:
        return

    # تشغيل الذكاء الاصطناعي فقط في الحالات التالية:
    # 1. إذا كانت الرسالة في جروب وتمت الإشارة (Mention) للبوت
    # 2. أو إذا كانت الرسالة رداً (Reply) مباشر على رسالة سابقة للبوت
    # 3. أو إذا كانت الرسالة مرسلة للبوت في الخاص (Private)
    bot_username = context.bot.username
    is_mentioned = message.text and f"@{bot_username}" in message.text
    is_reply_to_bot = message.reply_to_message and message.reply_to_message.from_user.id == context.bot.id
    is_private = update.effective_chat.type == "private"

    if is_mentioned or is_reply_to_bot or is_private:
        # تنظيف النص من اسم البوت إذا ذكر
        user_query = message.text.replace(f"@{bot_username}", "").strip()
        if not user_query:
            user_query = "مرحباً بك"

        # إرسال إشارة للمستخدم بأن البوت يقوم بالكتابة الآن (Typing...) لتبدو التجربة تفاعلية
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

        system_role = (
            "أنت مجيب وموجه شرعي وفكري ذكي جداً، تخاطب الإخوة والأخوات الموحدين في مجموعة نقاش دعوية وثقافية. "
            "أجوبتك مبنية على العقيدة الإسلامية الصحيحة، الولاء والبراء، ونصرة قضايا المسلمين والمجاهدين وثغور الأمة. "
            "كن ناصحاً، فصيحاً، حليماً مع المستفتين، وقوياً وحازماً في الحق. "
            "أجب مباشرة على تساؤل العضو بأسلوب شرعي رصين يجمع بين العلم الشرعي والوعي الواقعي المستند للقرآن والسنة."
        )
        
        # توليد الرد من Groq
        ai_reply = generate_ai_content(prompt=user_query, system_role=system_role, is_group_reply=True)
        
        # الرد المباشر على رسالة الشخص في المجموعة
        try:
            await message.reply_text(text=ai_reply)
            logger.info(f"تم الرد على العضو في الشات: {update.effective_chat.id}")
        except Exception as e:
            logger.error(f"فشل إرسال الرد في الشات: {e}")

def main():
    """تشغيل البوت وإعداد المهام"""
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    # الأوامر
    application.add_handler(CommandHandler("start", start))

    # معالجة كافة الرسائل النصية الموجهة للبوت في المجموعات أو الخاص
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_group_message))

    # إعداد مجدول المهام للنشر التلقائي في القناة العامة (كل 30 دقيقة = 1800 ثانية)
    job_queue = application.job_queue
    if job_queue:
        job_queue.run_repeating(auto_post_job, interval=1800, first=10)
        logger.info("تم تفعيل مجدول المهام للنشر الدوري في القناة (كل 30 دقيقة).")
    else:
        logger.error("خطأ: لم يتم تفعيل Job Queue في تطبيق التليجرام!")

    # بدء استقبال الرسائل والتحديثات
    logger.info("البوت يعمل الآن في القناة والمجموعة بنجاح...")
    application.run_polling()

if __name__ == '__main__':
    main()
