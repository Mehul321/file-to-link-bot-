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
        print(f"Message {message_id} auto-deleted.")
    except Exception as e:
        print(f"Error: {e}")

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "Welcome! Just send me any file, and I will provide a direct link instantly.")

@bot.message_handler(content_types=['document', 'video', 'audio', 'photo'])
def handle_files(message):
    file_id = None
    if message.document: file_id = message.document.file_id
    elif message.video: file_id = message.video.file_id
    elif message.audio: file_id = message.audio.file_id
    elif message.photo: file_id = message.photo[-1].file_id

    if file_id:
        # Get file path from Telegram
        file_info = bot.get_file(file_id)
        direct_url = f"https://api.telegram.org/file/bot{API_TOKEN}/{file_info.file_path}"

        # English Warning Note
        note = (
            "⚠️ **IMPORTANT NOTICE:**\n"
            "Please download or save this file to your storage now. "
            "This file will be **permanently deleted** from our server in 5 hours."
        )

        # Sending Direct Link and Note
        response_text = f"✅ **File Received!**\n\n🔗 **Direct Download Link:**\n`{direct_url}`\n\n{note}"
        
        sent_msg = bot.reply_to(message, response_text, parse_mode="Markdown")

        # Start 5-hour timer (18000 seconds) for both the file and the link message
        threading.Thread(target=delayed_delete, args=(message.chat.id, message.message_id, 18000)).start()
        threading.Thread(target=delayed_delete, args=(message.chat.id, sent_msg.message_id, 18000)).start()

bot.infinity_polling()
