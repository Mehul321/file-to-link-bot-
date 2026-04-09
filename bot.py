import os
import telebot
from telebot import types
from pymongo import MongoClient

# Environment Variables (Render se aayenge)
API_TOKEN = os.getenv('BOT_TOKEN')
MONGO_URI = os.getenv('MONGO_URI')

# MongoDB Setup
client = MongoClient(MONGO_URI)
db = client['file_to_link_bot']
collection = db['user_batches']

bot = telebot.TeleBot(API_TOKEN)

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "Namaste! Files bhejein, ye bot ab Database se connected hai.")

@bot.message_handler(content_types=['document', 'video', 'audio', 'photo'])
def handle_files(message):
    file_id = None
    if message.document: file_id = message.document.file_id
    elif message.video: file_id = message.video.file_id
    elif message.audio: file_id = message.audio.file_id
    elif message.photo: file_id = message.photo[-1].file_id

    if file_id:
        markup = types.InlineKeyboardMarkup(row_width=2)
        btn_link = types.InlineKeyboardButton("🔗 Get Link", callback_data=f"link_{file_id}")
        btn_batch = types.InlineKeyboardButton("📦 Get Batch", callback_data=f"batch_{file_id}")
        markup.add(btn_link, btn_batch)
        bot.reply_to(message, "Is file ka kya karna hai?", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    user_id = str(call.from_user.id)
    
    # 1. Single Link Logic
    if call.data.startswith("link_"):
        file_id = call.data.split("_")[1]
        file_info = bot.get_file(file_id)
        direct_url = f"https://api.telegram.org/file/bot{API_TOKEN}/{file_info.file_path}"
        bot.send_message(call.message.chat.id, f"✅ **Direct Link:**\n{direct_url}")
    
    # 2. Batch Logic
    elif call.data.startswith("batch_"):
        file_id = call.data.split("_")[1]
        collection.update_one(
            {"user_id": user_id},
            {"$push": {"files": file_id}},
            upsert=True
        )
        user_data = collection.find_one({"user_id": user_id})
        count = len(user_data['files'])
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🚀 Generate Batch Links", callback_data="gen_batch"))
        bot.send_message(call.message.chat.id, f"Batch mein add ho gaya! Total: {count}", reply_markup=markup)

    # 3. All Links Logic
    elif call.data == "gen_batch":
        user_data = collection.find_one({"user_id": user_id})
        if user_data and user_data['files']:
            res = "📦 **Aapke Batch Links:**\n\n"
            for i, f_id in enumerate(user_data['files'], 1):
                f_info = bot.get_file(f_id)
                res += f"{i}. https://api.telegram.org/file/bot{API_TOKEN}/{f_info.file_path}\n\n"
            bot.send_message(call.message.chat.id, res)
            collection.delete_one({"user_id": user_id}) # Clear batch after generation
        else:
            bot.answer_callback_query(call.id, "Batch khali hai!", show_alert=True)

bot.infinity_polling()
