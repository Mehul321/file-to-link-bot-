import os
import telebot
import time
import threading
import uuid
from telebot import types
from pymongo import MongoClient

# --- CONFIGURATION ---
API_TOKEN = "8398492174:AAH9s6x3YYKVTMTKsceE-LAzSwJPr-B1CRg"
MONGO_URI = "mongodb+srv://mehulrathod8514:IpEFuQmV5zFUWd0B@cluster0.91zmh.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"

bot = telebot.TeleBot(API_TOKEN)
client = MongoClient(MONGO_URI)
db = client['file_to_link_bot']
files_col = db['stored_files']
batches_col = db['user_batches']

# Get Bot Info
BOT_INFO = bot.get_me()
BOT_USERNAME = BOT_INFO.username

def delayed_delete(chat_id, message_id):
    time.sleep(18000) # 5 Hours
    try:
        bot.delete_message(chat_id, message_id)
    except: pass

@bot.message_handler(commands=['start'])
def start(message):
    args = message.text.split()
    if len(args) > 1:
        file_db_id = args[1]
        file_data = files_col.find_one({"_id": file_db_id})
        if file_data:
            f_id = file_data['file_id']
            f_type = file_data['file_type']
            cap = "✅ Here is your file! Save it now."
            
            # Yahan check ho raha hai ki file kis type ki hai
            try:
                if f_type == 'photo': bot.send_photo(message.chat.id, f_id, caption=cap)
                elif f_type == 'video': bot.send_video(message.chat.id, f_id, caption=cap)
                elif f_type == 'audio': bot.send_audio(message.chat.id, f_id, caption=cap)
                else: bot.send_document(message.chat.id, f_id, caption=cap)
                return
            except Exception as e:
                bot.reply_to(message, f"❌ Error: {e}")
                return
        else:
            bot.reply_to(message, "❌ Link expired or invalid.")
            return

    bot.reply_to(message, f"🔥 **Kingshortx Bot Active!**\n\nSend me any file to get a link like: `t.me/{BOT_USERNAME}?start=abc`")

@bot.message_handler(content_types=['document', 'video', 'audio', 'photo'])
def handle_files(message):
    file_id = None
    file_type = 'document'

    if message.document:
        file_id = message.document.file_id
        file_type = 'document'
    elif message.video:
        file_id = message.video.file_id
        file_type = 'video'
    elif message.audio:
        file_id = message.audio.file_id
        file_type = 'audio'
    elif message.photo:
        file_id = message.photo[-1].file_id
        file_type = 'photo'

    if file_id:
        db_id = str(uuid.uuid4())[:8]
        # Database mein type bhi save kar rahe hain
        files_col.insert_one({"_id": db_id, "file_id": file_id, "file_type": file_type})
        
        internal_link = f"https://t.me/{BOT_USERNAME}?start={db_id}"
        
        threading.Thread(target=delayed_delete, args=(message.chat.id, message.message_id)).start()

        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("📦 Add to Batch", callback_data=f"batch_{db_id}"))
        
        note = "\n\n⚠️ **IMPORTANT:** Deleted in 5 hours. Save now!"
        bot.reply_to(message, f"✅ **Your Link:**\n\n`{internal_link}`{note}", parse_mode="Markdown", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    # (Pichla batch wala logic same rahega...)
    pass

bot.remove_webhook()
bot.infinity_polling(skip_pending=True)
