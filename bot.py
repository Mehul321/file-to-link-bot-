import os
import telebot
import time
import threading
from telebot import types
from pymongo import MongoClient

# --- CONFIGURATION ---
API_TOKEN = "8398492174:AAH9s6x3YYKVTMTKsceE-LAzSwJPr-B1CRg"
MONGO_URI = "mongodb+srv://mehulrathod8514:IpEFuQmV5zFUWd0B@cluster0.91zmh.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
BOT_USERNAME = "Aapke_Bot_Ka_Username" # Bina @ ke (Example: MyFileBot)

bot = telebot.TeleBot(API_TOKEN)
client = MongoClient(MONGO_URI)
db = client['file_to_link_bot']
files_col = db['stored_files']
batches_col = db['user_batches']

def delayed_delete(chat_id, message_id):
    time.sleep(18000) # 5 Hours
    try:
        bot.delete_message(chat_id, message_id)
    except: pass

@bot.message_handler(commands=['start'])
def start(message):
    # Check if user clicked a file link (start parameter)
    args = message.text.split()
    if len(args) > 1:
        file_id_ref = args[1]
        file_data = files_col.find_one({"_id": file_id_ref})
        if file_data:
            bot.send_document(message.chat.id, file_data['file_id'], caption="✅ Here is your file!")
            return
        else:
            bot.reply_to(message, "❌ Link expired or invalid.")
            return

    bot.reply_to(message, "🔥 Internal File Bot Active! Send me a file.")

@bot.message_handler(content_types=['document', 'video', 'audio', 'photo'])
def handle_files(message):
    f_id = None
    if message.document: f_id = message.document.file_id
    elif message.video: f_id = message.video.file_id
    elif message.audio: f_id = message.audio.file_id
    elif message.photo: f_id = message.photo[-1].file_id

    if f_id:
        # Save file info in DB to create internal link
        db_id = str(message.message_id)
        files_col.update_one({"_id": db_id}, {"$set": {"file_id": f_id}}, upsert=True)
        
        # Create Telegram Internal Link
        internal_link = f"https://t.me/{BOT_USERNAME}?start={db_id}"
        
        threading.Thread(target=delayed_delete, args=(message.chat.id, message.message_id)).start()

        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("📦 Add to Batch", callback_data=f"batch_{db_id}"))
        
        note = "\n\n⚠️ **NOTE:** Save this file in 5 hours or it will be deleted."
        bot.reply_to(message, f"✅ **Internal Link:**\n{internal_link}{note}", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    user_id = str(call.from_user.id)
    if call.data.startswith("batch_"):
        file_db_id = call.data.split("_")[1]
        batches_col.update_one({"user_id": user_id}, {"$push": {"files": file_db_id}}, upsert=True)
        bot.answer_callback_query(call.id, "Added to batch!")
        
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🚀 Generate Batch", callback_data="gen_batch"))
        bot.send_message(call.message.chat.id, "File added! Click below to get all links.", reply_markup=markup)

    elif call.data == "gen_batch":
        user_data = batches_col.find_one({"user_id": user_id})
        if user_data and user_data['files']:
            res = "📦 **Your Batch Links (Telegram Internal):**\n\n"
            for i, f_ref in enumerate(user_data['files'], 1):
                res += f"{i}. https://t.me/{BOT_USERNAME}?start={f_ref}\n"
            bot.send_message(call.message.chat.id, res, disable_web_page_preview=True)
            batches_col.delete_one({"user_id": user_id})

bot.remove_webhook()
bot.infinity_polling(skip_pending=True)
