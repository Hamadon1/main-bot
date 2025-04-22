import telebot
import json
import random

TOKEN = '7105177180:AAGvw_qqid-VIVMwGMZIbo3L6cZCYQgj2DY'
ADMIN_ID = 6862331593 # Telegram ID-и админ

bot = telebot.TeleBot(TOKEN)

# Сохтани файл агар вуҷуд надорад
try:
    with open("data.json", "r") as f:
        db = json.load(f)
except:
    db = {"movies": {}, "channels": []}

# Захира кардани маълумот
def save_db():
    with open("data.json", "w") as f:
        json.dump(db, f)

# Санҷиши обуна
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

# Фармони /start
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

# Callback барои санҷиш
@bot.callback_query_handler(func=lambda call: call.data == "check_sub")
def check_sub(call):
    if is_subscribed(call.message.chat.id):
        bot.send_message(call.message.chat.id, "Офарин! Шумо метавонед ботро истифода баред.")
    else:
        bot.send_message(call.message.chat.id, "Лутфан аввал обуна шавед.")

# Фармони /panel
@bot.message_handler(commands=["panel"])
def panel(msg):
    if msg.from_user.id == ADMIN_ID:
        markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("➕ Иловаи Филм", "➕ Иловаи Канал")
        bot.send_message(msg.chat.id, "Панели админ:", reply_markup=markup)

# Ҳолат барои филм ё канал
user_states = {}

@bot.message_handler(func=lambda msg: msg.text == "➕ Иловаи Филм" and msg.from_user.id == ADMIN_ID)
def add_movie(msg):
    user_states[msg.chat.id] = "waiting_for_movie"
    bot.send_message(msg.chat.id, "Лутфан филмро фиристед:")

@bot.message_handler(func=lambda msg: msg.text == "➕ Иловаи Канал" and msg.from_user.id == ADMIN_ID)
def add_channel(msg):
    user_states[msg.chat.id] = "waiting_for_channel"
    bot.send_message(msg.chat.id, "Номи канал ё линкро фиристед (масалан: @channel):")

@bot.message_handler(content_types=["video"])
def save_movie(msg):
    if user_states.get(msg.chat.id) == "waiting_for_movie":
        movie_id = str(random.randint(1000, 9999))
        db["movies"][movie_id] = msg.video.file_id
        save_db()
        bot.send_message(msg.chat.id, f"Филм сабт шуд. Қулф ID: {movie_id}")
        user_states.pop(msg.chat.id)

@bot.message_handler(func=lambda msg: user_states.get(msg.chat.id) == "waiting_for_channel")
def save_channel(msg):
    db["channels"].append(msg.text)
    save_db()
    bot.send_message(msg.chat.id, f"Канал '{msg.text}' сабт шуд.")
    user_states.pop(msg.chat.id)

# Корбари оддӣ ID мефиристад
@bot.message_handler(func=lambda msg: msg.text.isdigit() and len(msg.text) == 4)
def send_movie(msg):
    movie_id = msg.text
    if is_subscribed(msg.chat.id):
        if movie_id in db["movies"]:
            bot.send_video(msg.chat.id, db["movies"][movie_id])
        else:
            bot.send_message(msg.chat.id, "Филм ёфт нашуд.")
    else:
        start(msg)

# Запуск
bot.infinity_polling()
