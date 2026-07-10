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
        return "خطأ: لم يتم تفعيل مفتاح GROQ_API_KEY في الـ Variables الخاصة بـ Railway."
    
    url = "https://groq.com"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY.strip()}",
        "Content-Type": "application/json"
    }
    
    # استخدام النموذج المجاني الأكثر استقراراً وسرعة ودعماً للغة العربية حالياً
    data = {
        "model": "llama-3.1-8b-instant",
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
    except urllib.error.HTTPError as http_err:
        error_msg = http_err.read().decode('utf-8')
        logger.error(f"خطأ HTTP من Groq API: {error_msg}")
        try:
            # محاولة استخراج رسالة الخطأ الصريحة القادمة من موقع Groq
            parsed_err = json.loads(error_msg)
            return f"خطأ من سيرفر Groq: {parsed_err['error']['message']}"
        except:
            return f"خطأ HTTP رمز: {http_err.code}"
    except Exception as e:
        logger.error(f"فشل الاتصال بـ Groq API بسبب: {e}")
        return f"فشل الاتصال البرمجي: {str(e)}"

# خيط الجدولة الدوري المستقل (كل 30 دقيقة) بدون تداخل برمي
def background_posting_thread(bot_token):
    logger.info("بدء تشغيل خيط الخلفية للنشر الآلي...")
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
            
            # التأكد أن الرد عبارة عن نص الموعظة وليس رسالة خطأ تبدأ بـ "خطأ" أو "فشل"
            if post_content and not post_content.startswith("خطأ") and not post_content.startswith("فشل"):
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
                logger.error(f"تم تخطي النشر الدوري بسبب خطأ السيرفر: {post_content}")
        else:
            logger.error("خطأ: تأكد من كتابة معرف القناة ورمز التوكن بشكل سليم.")
            
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
    
    # إرسال الإجابة مباشرة للمستخدم (سواء كانت الفتوى أو نص الخطأ الصريح القادم من المنصة للتحقق)
    await update.message.reply_text(groq_reply, reply_to_message_id=update.message.message_id)

def main() -> None:
    TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    if not TOKEN:
        logger.error("خطأ حرج: لم يتم العثور على متغير البيئة TELEGRAM_BOT_TOKEN")
        return

    threading.Thread(target=background_posting_thread, args=(TOKEN,), daemon=True).start()

    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("تم إقلاع البوت وتثبيت الإعدادات بنجاح...")
    application.run_polling()

if __name__ == '__main__':
    main()
