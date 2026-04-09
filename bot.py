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
collection = db['user_batches']

# Function to delete message after 5 hours
def delayed_delete(chat_id, message_id, delay):
    time.sleep(delay)
    try:
        bot.delete_message(chat_id, message_id)
    except Exception:
        pass

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "🔥 Batch & Link Bot Active!\n\nSend files to get started.")

@bot.message_handler(content_types=['document', 'video', 'audio', 'photo'])
def handle_files(message):
    file_id = None
    if message.document: file_id = message.document.file_id
    elif message.video: file_id = message.video.file_id
    elif message.audio: file_id = message.audio.file_id
    elif message.photo: file_id = message.photo[-1].file_id

    if file_id:
        # 5 Hours Timer for the original file
        threading.Thread(target=delayed_delete, args=(message.chat.id, message.message_id, 18000)).start()
        
        markup = types.InlineKeyboardMarkup(row_width=2)
        btn_link = types.InlineKeyboardButton("🔗 Get Single Link", callback_data=f"link_{file_id}")
        btn_batch = types.InlineKeyboardButton("📦 Add to Batch", callback_data=f"batch_{file_id}")
        markup.add(btn_link, btn_batch)
        
        bot.reply_to(message, "Choose an option:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    user_id = str(call.from_user.id)
    note = "\n\n⚠️ **NOTICE:** Save files now. They will be deleted in 5 hours."

    if call.data.startswith("link_"):
        file_id = call.data.split("_")[1]
        file_info = bot.get_file(file_id)
        direct_url = f"https://api.telegram.org/file/bot{API_TOKEN}/{file_info.file_path}"
        bot.send_message(call.message.chat.id, f"✅ **Direct Link:**\n`{direct_url}`{note}", parse_mode="Markdown")
    
    elif call.data.startswith("batch_"):
        file_id = call.data.split("_")[1]
        collection.update_one({"user_id": user_id}, {"$push": {"files": file_id}}, upsert=True)
        
        user_data = collection.find_one({"user_id": user_id})
        count = len(user_data['files'])
        
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🚀 Generate Batch Links", callback_data="gen_batch"))
        bot.send_message(call.message.chat.id, f"Added to batch! Total: {count}", reply_markup=markup)

    elif call.data == "gen_batch":
        user_data = collection.find_one({"user_id": user_id})
        if user_data and user_data['files']:
            res = "📦 **Your Batch Links:**\n\n"
            for i, f_id in enumerate(user_data['files'], 1):
                f_info = bot.get_file(f_id)
                res += f"{i}. https://api.telegram.org/file/bot{API_TOKEN}/{f_info.file_path}\n\n"
            
            res += note
            bot.send_message(call.message.chat.id, res, disable_web_page_preview=True)
            collection.delete_one({"user_id": user_id})
        else:
            bot.answer_callback_query(call.id, "Batch is empty!", show_alert=True)

bot.infinity_polling()
