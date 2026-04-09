import os
import telebot
import time
import threading
from telebot import types
from pymongo import MongoClient

# --- CONFIGURATION ---
API_TOKEN = "8398492174:AAH9s6x3YYKVTMTKsceE-LAzSwJPr-B1CRg"
MONGO_URI = "mongodb+srv://mehulrathod8514:IpEFuQmV5zFUWd0B@cluster0.91zmh.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
# ----------------------

bot = telebot.TeleBot(API_TOKEN)
client = MongoClient(MONGO_URI)
db = client['file_to_link_bot']
files_col = db['stored_files']
batches_col = db['user_batches']

# Bot ka username nikalne ke liye
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
    # Agar user link se aaya hai (t.me/bot?start=id)
    if len(args) > 1:
        file_db_id = args[1]
        file_data = files_col.find_one({"_id": file_db_id})
        if file_data:
            # File seedha Telegram mein bhej raha hai
            bot.send_document(message.chat.id, file_data['file_id'], caption="✅ Here is your file! Save it now.")
            return
        else:
            bot.reply_to(message, "❌ Sorry, this link has expired or is invalid.")
            return

    bot.reply_to(message, "🔥 **Telegram File Store Active!**\n\nSend me any file to get an internal link.")

@bot.message_handler(content_types=['document', 'video', 'audio', 'photo'])
def handle_files(message):
    f_id = None
    if message.document: f_id = message.document.file_id
    elif message.video: f_id = message.video.file_id
    elif message.audio: f_id = message.audio.file_id
    elif message.photo: f_id = message.photo[-1].file_id

    if f_id:
        # DB mein save kar rahe hain (Random ID ke saath)
        import uuid
        db_id = str(uuid.uuid4())[:8] # Choti unique ID
        files_col.insert_one({"_id": db_id, "file_id": f_id})
        
        # Telegram Internal Link
        internal_link = f"https://t.me/{BOT_USERNAME}?start={db_id}"
        
        # 5 Hours Delete Timer
        threading.Thread(target=delayed_delete, args=(message.chat.id, message.message_id)).start()

        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("📦 Add to Batch", callback_data=f"batch_{db_id}"))
        
        note = "\n\n⚠️ **IMPORTANT:** This file will be deleted in 5 hours. Download it now!"
        bot.reply_to(message, f"✅ **Your Internal Link:**\n\n`{internal_link}`{note}", parse_mode="Markdown", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    user_id = str(call.from_user.id)
    if call.data.startswith("batch_"):
        file_db_id = call.data.split("_")[1]
        batches_col.update_one({"user_id": user_id}, {"$push": {"files": file_db_id}}, upsert=True)
        bot.answer_callback_query(call.id, "Added to batch!")
        
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🚀 Generate Batch Links", callback_data="gen_batch"))
        bot.send_message(call.message.chat.id, "Added! Click below when done.", reply_markup=markup)

    elif call.data == "gen_batch":
        user_data = batches_col.find_one({"user_id": user_id})
        if user_data and user_data.get('files'):
            res = "📦 **Batch Links (Telegram Only):**\n\n"
            for i, f_ref in enumerate(user_data['files'], 1):
                res += f"{i}. https://t.me/{BOT_USERNAME}?start={f_ref}\n"
            
            bot.send_message(call.message.chat.id, res, disable_web_page_preview=True)
            batches_col.delete_one({"user_id": user_id})

bot.remove_webhook()
bot.infinity_polling(skip_pending=True)
