from flask import Flask, request
import telebot
import json
import random

TOKEN = '7105177180:AAGvw_qqid-VIVMwGMZIbo3L6cZCYQgj2DY'
ADMIN_ID = 6862331593  # Telegram ID-и админ

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# Базаи маълумот
try:
    with open("data.json", "r") as f:
        db = json.load(f)
except:
    db = {"movies": {}, "channels": []}

def save_db():
    with open("data.json", "w") as f:
        json.dump(db, f)

def is_subscribed(user_id):
    for channel in db["channels"]:
        try:
            status = bot.get_chat_member(channel, user_id).status
            if status in ['member', 'administrator', 'creator']:
                continue
            else:
                return False
        except:
            return False
    return True

user_states = {}
movie_info_temp = {}

# Роут барои webhook
@app.route(f'/{TOKEN}', methods=['POST'])
def webhook():
    update = telebot.types.Update.de_json(request.stream.read().decode("utf-8"))
    bot.process_new_updates([update])
    return 'ok', 200

@app.route('/')
def index():
    return "Bot is running!", 200

# Хандлерҳо
@bot.message_handler(commands=["start"])
def start(msg):
    if is_subscribed(msg.chat.id):
        bot.send_message(msg.chat.id, "Хуш омадед. Барои гирифтани филм қулф ID фиристед.")
    else:
        markup = telebot.types.InlineKeyboardMarkup()
        for ch in db["channels"]:
            markup.add(telebot.types.InlineKeyboardButton("Обуна шудан", url=f"https://t.me/{ch.replace('@', '')}"))
        markup.add(telebot.types.InlineKeyboardButton("Санҷиш", callback_data="check_sub"))
        bot.send_message(msg.chat.id, "Аввал ба каналҳо обуна шавед:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "check_sub")
def check_sub(call):
    if is_subscribed(call.message.chat.id):
        bot.send_message(call.message.chat.id, "Офарин! Шумо метавонед ботро истифода баред.")
    else:
        bot.send_message(call.message.chat.id, "Лутфан аввал обуна шавед.")

@bot.message_handler(commands=["panel"])
def panel(msg):
    if msg.from_user.id == ADMIN_ID:
        markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("➕ Иловаи Филм", "➕ Иловаи Канал")
        markup.add("❌ Нест кардани Филм", "❌ Нест кардани Канал")
        bot.send_message(msg.chat.id, "Панели админ:", reply_markup=markup)

@bot.message_handler(func=lambda msg: msg.text == "➕ Иловаи Филм" and msg.from_user.id == ADMIN_ID)
def add_movie(msg):
    user_states[msg.chat.id] = "waiting_for_movie"
    bot.send_message(msg.chat.id, "Филмро равон кунед:")

@bot.message_handler(func=lambda msg: msg.text == "➕ Иловаи Канал" and msg.from_user.id == ADMIN_ID)
def add_channel(msg):
    user_states[msg.chat.id] = "waiting_for_channel"
    bot.send_message(msg.chat.id, "Номи каналро равон кунед (мисол: @kanal):")

@bot.message_handler(func=lambda msg: msg.text == "❌ Нест кардани Филм" and msg.from_user.id == ADMIN_ID)
def delete_movie(msg):
    user_states[msg.chat.id] = "waiting_for_delete_movie"
    bot.send_message(msg.chat.id, "ID-и филмро нависед барои нест кардан:")

@bot.message_handler(func=lambda msg: msg.text == "❌ Нест кардани Канал" and msg.from_user.id == ADMIN_ID)
def delete_channel(msg):
    if db["channels"]:
        user_states[msg.chat.id] = "waiting_for_delete_channel"
        chs = "\n".join([f"{i+1}. {ch}" for i, ch in enumerate(db["channels"])])
        bot.send_message(msg.chat.id, f"Ин рақамро нависед:\n{chs}")
    else:
        bot.send_message(msg.chat.id, "Канал ёфт нашуд.")

@bot.message_handler(content_types=["video"])
def save_movie(msg):
    if user_states.get(msg.chat.id) == "waiting_for_movie":
        movie_id = str(random.randint(1000, 9999))
        movie_info_temp[msg.chat.id] = {"id": movie_id, "file_id": msg.video.file_id}
        user_states[msg.chat.id] = "waiting_for_movie_info"
        bot.send_message(msg.chat.id, "Маълумоти филмро равон кунед ё /skip нависед:")

@bot.message_handler(func=lambda msg: user_states.get(msg.chat.id) == "waiting_for_movie_info")
def add_movie_info(msg):
    movie_info = "" if msg.text == "/skip" else msg.text
    movie_id = movie_info_temp[msg.chat.id]["id"]
    file_id = movie_info_temp[msg.chat.id]["file_id"]

    db["movies"][movie_id] = {"file_id": file_id, "info": movie_info}
    save_db()
    bot.send_message(msg.chat.id, f"Сабт шуд. Қулф ID: {movie_id}")
    user_states.pop(msg.chat.id)
    movie_info_temp.pop(msg.chat.id)

@bot.message_handler(func=lambda msg: user_states.get(msg.chat.id) == "waiting_for_channel")
def save_channel(msg):
    db["channels"].append(msg.text)
    save_db()
    bot.send_message(msg.chat.id, f"Канал {msg.text} сабт шуд.")
    user_states.pop(msg.chat.id)

@bot.message_handler(func=lambda msg: user_states.get(msg.chat.id) == "waiting_for_delete_movie")
def process_delete_movie(msg):
    movie_id = msg.text
    if movie_id in db["movies"]:
        db["movies"].pop(movie_id)
        save_db()
        bot.send_message(msg.chat.id, "Филм нест шуд.")
    else:
        bot.send_message(msg.chat.id, "Филм ёфт нашуд.")
    user_states.pop(msg.chat.id)

@bot.message_handler(func=lambda msg: user_states.get(msg.chat.id) == "waiting_for_delete_channel")
def process_delete_channel(msg):
    try:
        index = int(msg.text) - 1
        if 0 <= index < len(db["channels"]):
            ch = db["channels"].pop(index)
            save_db()
            bot.send_message(msg.chat.id, f"{ch} нест шуд.")
        else:
            bot.send_message(msg.chat.id, "Рақам нодуруст.")
    except:
        bot.send_message(msg.chat.id, "Лутфан рақам нависед.")
    user_states.pop(msg.chat.id)

@bot.message_handler(func=lambda msg: msg.text.isdigit() and len(msg.text) == 4)
def send_movie(msg):
    movie_id = msg.text
    if is_subscribed(msg.chat.id):
        if movie_id in db["movies"]:
            data = db["movies"][movie_id]
            bot.send_video(msg.chat.id, data["file_id"])
            if data["info"]:
                bot.send_message(msg.chat.id, data["info"])
        else:
            bot.send_message(msg.chat.id, "Филм ёфт нашуд.")
    else:
        start(msg)

# Webhook-ро насб мекунем
bot.remove_webhook()
bot.set_webhook(url=f"https://main-bot-7ydv.onrender.com/7105177180:AAGvw_qqid-VIVMwGMZIbo3L6cZCYQgj2DY")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
