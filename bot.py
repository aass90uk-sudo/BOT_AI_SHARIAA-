import os
import logging
import json
import time
import threading
import urllib.request
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# إعدادات التسجيل لمراقبة الأخطاء
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# جلب المتغيرات السرية المحدثة من بيئة تشغيل Railway
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID")

# دالة الاتصال القياسية المعتمدة لدى سيرفرات Groq
def ask_groq(system_prompt, user_prompt):
    if not GROQ_API_KEY:
        logger.error("خطأ: لم يتم تفعيل مفتاح GROQ_API_KEY في الـ Variables.")
        return None
    
    # الرابط والمنافذ القياسية لمنصة Groq Cloud
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    
    # صياغة الطلب وهيكل النموذج الأكثر استقراراً ودعماً للعربية مجاناً
    data = {
        "model": "llama3-8b-8192",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 0.6
    }
    
    try:
        req = urllib.request.Request(
            url, 
            data=json.dumps(data).encode('utf-8'), 
            headers=headers, 
            method='POST'
        )
        with urllib.request.urlopen(req, timeout=15) as response:
            res_data = json.loads(response.read().decode('utf-8'))
            return res_data['choices']['message']['content']
    except Exception as e:
        logger.error(f"فشل الاتصال بـ Groq API بسبب: {e}")
        return None

# خيط الجدولة الدوري المستقل (كل 30 دقيقة) بدون تداخل برمي
def background_posting_thread(bot_token):
    logger.info("بدء تشغيل خيط الخلفية للنشر الآلي...")
    # مهلة قصيرة عند إقلاع السيرفر لأول مرة لضمان استقرار الاتصال
    time.sleep(15)
    
    system_prompt = (
        "أنت كاتب وموجه إسلامي بليغ. اكتب موعظة إيمانية حماسية مكثفة وقصيرة "
        "(مناسبة لنشرها كمنشور تليجرام سريع ومؤثر). "
        "يجب أن يركز المنشور بشكل قوي ومباشر على أحد المواضيع التالية بالتناوب: "
        "1) ترسيخ عقيدة الولاء والبراء في نفوس الأمة. "
        "2) بيان أهمية الجهاد وثبات الأمة وعزتها. "
        "3) مراغمة الكفار وأعداء الدين في جزيرة العرب. "
        "4) الدعاء المستمر بحرقة وتضرع لأبطال وثغور المجاهدين في كل بقاع الأرض لحفظهم ونصرحهم. "
        "استخدم أسلوباً قوياً، جزلاً، بليغاً، مليئاً بالآيات والأحاديث المناسبة، "
        "مع استخدام علامات الترقيم والتنسيق لإعطاء المنشور طابعاً حماسياً."
    )
    user_prompt = "اكتب المنشور الدوري الحماسي الآن بجودة وبلاغة عالية وبدون مقدمات."

    while True:
        if CHANNEL_ID and bot_token:
            logger.info("جاري طلب الموعظة التلقائية من سيرفر Groq...")
            post_content = ask_groq(system_prompt, user_prompt)
            
            if post_content:
                # النشر المباشر عبر بروتوكول تليجرام الصريح تفادياً لانهيار الحزم
                telegram_url = f"https://telegram.org{bot_token}/sendMessage"
                post_data = {
                    "chat_id": CHANNEL_ID,
                    "text": post_content,
                    "parse_mode": "Markdown"
                }
                try:
                    req = urllib.request.Request(
                        telegram_url, 
                        data=json.dumps(post_data).encode('utf-8'), 
                        headers={"Content-Type": "application/json"}, 
                        method='POST'
                    )
                    with urllib.request.urlopen(req) as resp:
                        logger.info("تم بث الموعظة بنجاح داخل القناة.")
                except Exception as send_error:
                    logger.error(f"فشل إرسال النص إلى القناة: {send_error}")
            else:
                logger.error("فشل في استلام النص من Groq.")
        else:
            logger.error("خطأ: تأكد من كتابة معرف القناة ورمز التوكن بشكل سليم.")
            
        # الانتظار لمدة 30 دقيقة كاملة (1800 ثانية) قبل توليد المنشور التالي
        time.sleep(1800)

# استقبال أوامر /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_name = update.effective_user.first_name
    welcome_text = (
        f"مرحباً بك يا {user_name} في بوت القناة الشرعي والوعظي الفقهي.\n\n"
        "البوت جاهز تماماً الآن لتلقي واستقبال أسئلة الإخوة والأخوات والإجابة عليها عبر منصة Groq.\n"
        "كما أن نظام بث المواعظ الدوري يعمل تلقائياً كل نصف ساعة داخل القناة."
    )
    await update.message.reply_text(welcome_text)

# فحص الرسائل والرد الشرعي الآلي في الخاص
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_message = update.message.text
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

    system_prompt = (
        "أنت مستشار شرعي وبوت فقهي مخصص لخدمة الإخوة والأخوات الموحدين. "
        "أجب على الأسئلة الدينية والفقهية بدقة بناءً على الكتاب والسنة بفهم سلف الأمة مع ذكر الأدلة. "
        "يجب أن يكون أسلوبك في غاية الأدب واللطف والرفق واللين المستمر."
    )
    
    groq_reply = ask_groq(system_prompt, user_message)
    
    if groq_reply:
        await update.message.reply_text(groq_reply, reply_to_message_id=update.message.message_id)
    else:
        await update.message.reply_text(
            "جزاكم الله خيراً، حصل خطأ مؤقت في الاتصال بالسيرفر الوعظي، يرجى إعادة إرسال السؤال مرة أخرى.", 
            reply_to_message_id=update.message.message_id
        )

def main() -> None:
    TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    if not TOKEN:
        logger.error("خطأ حرج: لم يتم العثور على متغير البيئة TELEGRAM_BOT_TOKEN")
        return

    # تشغيل خيط الجدولة بشكل مستقل قبل بدء عملية الـ Polling الأساسية لتجنب التعليق
    threading.Thread(target=background_posting_thread, args=(TOKEN,), daemon=True).start()

    # إنشاء تطبيق التليجرام الأساسي بنقاء واستقرار تام
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("تم إقلاع البوت وتثبيت الإعدادات بنجاح...")
    application.run_polling()

if __name__ == '__main__':
    main()
