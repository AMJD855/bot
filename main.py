from telebot import TeleBot
import telebot
from telebot import types

# قائمة بالـ IDs المسموح لهم
ALLOWED_IDS = {6237935028}  # أضف هنا IDs المسموح لهم

# استيراد الكود الأصلي
from original_bot import bot, TOKEN  # تأكد من اسم الملف الأصلي

# إنشاء نسخة من البوت مع نظام التحقق
verified_bot = TeleBot(TOKEN)

# ديكوراتور للتحقق من الرسائل
def check_access(func):
    def wrapper(message):
        user_id = message.from_user.id
        if user_id not in ALLOWED_IDS:
            verified_bot.reply_to(message, "⛔ غير مصرح لك باستخدام هذا البوت")
            return
        return func(message)
    return wrapper

# ديكوراتور للتحقق من الـ callbacks
def check_access_callback(func):
    def wrapper(call):
        user_id = call.from_user.id
        if user_id not in ALLOWED_IDS:
            verified_bot.answer_callback_query(call.id, "⛔ غير مصرح لك باستخدام هذا البوت", show_alert=True)
            return
        return func(call)
    return wrapper

# معالجة الأوامر والرسائل
@verified_bot.message_handler(commands=['start', 'admin', 'help'])
@check_access
def verified_commands(message):
    bot.process_new_messages([message])

@verified_bot.message_handler(content_types=['document'])
@check_access
def verified_documents(message):
    bot.process_new_messages([message])

# معالجة الـ callbacks
@verified_bot.callback_query_handler(func=lambda call: True)
@check_access_callback
def verified_callbacks(call):
    # معالجة خاصة لزر التحقق من الاشتراك
    if call.data == 'check_subscription':
        try:
            member = verified_bot.get_chat_member('@blackena', call.from_user.id)
            if member.status in ['member', 'administrator', 'creator']:
                if call.message:
                    verified_bot.delete_message(call.message.chat.id, call.message.message_id)
                show_main_menu(call.from_user.id)
            else:
                verified_bot.answer_callback_query(call.id, "⚠️ لم تشترك في القناة بعد!", show_alert=True)
        except Exception as e:
            print(f"Error checking subscription: {e}")
            verified_bot.answer_callback_query(call.id, "⚠️ حدث خطأ في التحقق من الاشتراك", show_alert=True)
    else:
        # تمرير الـ callback للبوت الأصلي
        bot.callback_query_handler(func=lambda c: True)(lambda c: None)  # تهيئة
        bot.process_new_callback_query([call])

# دالة مساعدة لعرض القائمة الرئيسية
def show_main_menu(user_id):
    markup = types.InlineKeyboardMarkup()
    # ... (نفس أزرار القائمة الرئيسية من الكود الأصلي)
    verified_bot.send_message(user_id, "مرحباً بك في البوت...", reply_markup=markup)

if __name__ == '__main__':
    print("🤖 البوت يعمل بنظام التحقق المعدل...")
    verified_bot.polling(none_stop=True)
