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

# جلب المتغيرات السرية من بيئة التشغيل
XAI_API_KEY = os.getenv("XAI_API_KEY")
CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID")

def ask_grok(system_prompt, user_prompt):
    if not XAI_API_KEY:
        logger.error("خطأ: لم يتم ضبط مفتاح Grok")
        return None
    
    url = "https://x.ai"
    headers = {
        "Authorization": f"Bearer {XAI_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "grok-2-latest",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
    }
    
    try:
        req = urllib.request.Request(url, data=json.dumps(data).encode('utf-8'), headers=headers, method='POST')
        with urllib.request.urlopen(req) as response:
            res_data = json.loads(response.read().decode('utf-8'))
            return res_data['choices']['message']['content']
    except Exception as e:
        logger.error(f"خطأ أثناء الاتصال بـ Grok API: {e}")
        return None

def background_posting_thread(bot_token):
    logger.info("تم إطلاق خيط النشر الدوري المستقل بنجاح...")
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
        "مع استخدام علامات الترقيم والتنسيق (Bold) لإعطاء المنشور طابعاً حماسياً."
    )
    user_prompt = "اكتب المنشور الدوري الحماسي الآن بجودة وبلاغة عالية."

    while True:
        if CHANNEL_ID and bot_token:
            logger.info("جاري توليد المنشور الدوري من Grok...")
            post_content = ask_grok(system_prompt, user_prompt)
            
            if post_content:
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
                        logger.info("تم نشر الموعظة بنجاح في القناة المربوطة.")
                except Exception as send_error:
                    logger.error(f"فشل إرسال الرسالة للقناة: {send_error}")
            else:
                logger.error("فشل توليد المحتوى من Grok.")
        else:
            logger.error("خطأ: لم يتم ضبط الإعدادات بشكل صحيح في المتغيرات.")
            
        time.sleep(1800)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_name = update.effective_user.first_name
    welcome_text = (
        f"أهلاً بك يا {user_name} في بوت القناة الشرعي والوعظي الدوري.\n\n"
        "البوت مستعد الآن لاستقبال أسئلة الإخوة والأخوات والرد عليها عبر Grok.\n"
        "ونظام النشر الدوري يعمل تلقائياً كل 30 دقيقة في القناة المربوطة."
    )
    await update.message.reply_text(welcome_text)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_message = update.message.text
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

    system_prompt = (
        "أنت مستشار شرعي وبوت فقهي مخصص لخدمة الإخوة والأخوات الموحدين. "
        "أجب على الأسئلة الدينية والفقهية بدقة بناءً على الكتاب والسنة بفهم سلف الأمة مع ذكر الأدلة. "
        "يجب أن يكون أسلوبك في غاية الأدب واللطف والرفق."
    )
    
    grok_reply = ask_grok(system_prompt, user_message)
    
    if grok_reply:
        await update.message.reply_text(grok_reply, reply_to_message_id=update.message.message_id)
    else:
        await update.message.reply_text("حصل خطأ أثناء معالجة السؤال، يرجى المحاولة لاحقاً.")

def main() -> None:
    TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    if not TOKEN:
        logger.error("خطأ: لم يتم العثور على TELEGRAM_BOT_TOKEN")
        return

    threading.Thread(target=background_posting_thread, args=(TOKEN,), daemon=True).start()

    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("تم تشغيل البوت بنجاح واستقرار عالي...")
    application.run_polling()

if __name__ == '__main__':
    main()
