import telebot
import json
import random
from flask import Flask, request

TOKEN = '7574268255:AAH6pOhS_-SamVqmieHMrh6JV3AV5SjWR1s'
ADMIN_ID = 6862331593

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# Загрузка базы
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

user_states = {}
movie_info_temp = {}

@bot.message_handler(func=lambda msg: msg.text == "➕ Иловаи Филм" and msg.from_user.id == ADMIN_ID)
def add_movie(msg):
    user_states[msg.chat.id] = "waiting_for_movie"
    bot.send_message(msg.chat.id, "Лутфан филмро фиристед:")

@bot.message_handler(func=lambda msg: msg.text == "➕ Иловаи Канал" and msg.from_user.id == ADMIN_ID)
def add_channel(msg):
    user_states[msg.chat.id] = "waiting_for_channel"
    bot.send_message(msg.chat.id, "Номи канал ё линкро фиристед (масалан: @channel):")

@bot.message_handler(func=lambda msg: msg.text == "❌ Нест кардани Филм" and msg.from_user.id == ADMIN_ID)
def delete_movie(msg):
    user_states[msg.chat.id] = "waiting_for_delete_movie"
    bot.send_message(msg.chat.id, "ID филмро барои нест кардан фиристед:")

@bot.message_handler(func=lambda msg: msg.text == "❌ Нест кардани Канал" and msg.from_user.id == ADMIN_ID)
def delete_channel(msg):
    if db["channels"]:
        user_states[msg.chat.id] = "waiting_for_delete_channel"
        channel_list = "\n".join([f"{i+1}. {ch}" for i, ch in enumerate(db["channels"])])
        bot.send_message(msg.chat.id, f"Рақами каналро барои нест кардан интихоб кунед:\n{channel_list}")
    else:
        bot.send_message(msg.chat.id, "Ягон канал ёфт нашуд.")

@bot.message_handler(content_types=["video"])
def save_movie(msg):
    if user_states.get(msg.chat.id) == "waiting_for_movie":
        movie_id = str(random.randint(1000, 9999))
        movie_info_temp[msg.chat.id] = {
            "id": movie_id,
            "file_id": msg.video.file_id
        }
        user_states[msg.chat.id] = "waiting_for_movie_info"
        bot.send_message(msg.chat.id, "Лутфан маълумоти филмро фиристед ё /skip:")

@bot.message_handler(func=lambda msg: user_states.get(msg.chat.id) == "waiting_for_movie_info")
def add_movie_info(msg):
    movie_info = "" if msg.text == "/skip" else msg.text
    movie_id = movie_info_temp[msg.chat.id]["id"]
    file_id = movie_info_temp[msg.chat.id]["file_id"]

    db["movies"][movie_id] = {
        "file_id": file_id,
        "info": movie_info
    }
    save_db()
    bot.send_message(msg.chat.id, f"Филм сабт шуд. Қулф ID: {movie_id}")
    user_states.pop(msg.chat.id)
    movie_info_temp.pop(msg.chat.id)

@bot.message_handler(func=lambda msg: user_states.get(msg.chat.id) == "waiting_for_channel")
def save_channel(msg):
    db["channels"].append(msg.text)
    save_db()
    bot.send_message(msg.chat.id, f"Канал '{msg.text}' сабт шуд.")
    user_states.pop(msg.chat.id)

@bot.message_handler(func=lambda msg: user_states.get(msg.chat.id) == "waiting_for_delete_movie")
def process_delete_movie(msg):
    movie_id = msg.text
    if movie_id in db["movies"]:
        db["movies"].pop(movie_id)
        save_db()
        bot.send_message(msg.chat.id, f"Филм бо ID {movie_id} нест карда шуд.")
    else:
        bot.send_message(msg.chat.id, "Филм бо чунин ID ёфт нашуд.")
    user_states.pop(msg.chat.id)

@bot.message_handler(func=lambda msg: user_states.get(msg.chat.id) == "waiting_for_delete_channel")
def process_delete_channel(msg):
    try:
        index = int(msg.text) - 1
        if 0 <= index < len(db["channels"]):
            deleted_channel = db["channels"].pop(index)
            save_db()
            bot.send_message(msg.chat.id, f"Канал '{deleted_channel}' нест карда шуд.")
        else:
            bot.send_message(msg.chat.id, "Рақами канал нодуруст аст.")
    except ValueError:
        bot.send_message(msg.chat.id, "Лутфан рақами каналро фиристед.")
    user_states.pop(msg.chat.id)

@bot.message_handler(func=lambda msg: msg.text.isdigit() and len(msg.text) == 4)
def send_movie(msg):
    movie_id = msg.text
    if is_subscribed(msg.chat.id):
        if movie_id in db["movies"]:
            movie_data = db["movies"][movie_id]
            bot.send_video(msg.chat.id, movie_data["file_id"])
            if movie_data["info"]:
                bot.send_message(msg.chat.id, movie_data["info"])
        else:
            bot.send_message(msg.chat.id, "Филм ёфт нашуд.")
    else:
        start(msg)

# Роҳбарии веб-сервер
@app.route('/')
def index():
    return 'Bot is working!'

@app.route('/' + TOKEN, methods=['POST'])
def webhook():
    json_string = request.get_data().decode('utf-8')
    update = telebot.types.Update.de_json(json_string)
    bot.process_new_updates([update])
    return 'ok', 200

@app.route('/setwebhook', methods=['GET'])
def set_webhook():
    webhook_url = f"https://main-bot-7ydv.onrender.com/{TOKEN}"
    bot.remove_webhook()
    bot.set_webhook(url=webhook_url)
    return "Webhook set!"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
