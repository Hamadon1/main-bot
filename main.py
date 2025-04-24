from flask import Flask, request
import telebot
import json
import random
import os
from datetime import datetime

TOKEN = '7105177180:AAGvw_qqid-VIVMwGMZIbo3L6cZCYQgj2DY'
ADMIN_ID = 6862331593  # Telegram ID-и админ

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# Базаи маълумот
try:
    with open("data.json", "r", encoding="utf-8") as f:
        db = json.load(f)
except:
    db = {
        "movies": {}, 
        "channels": [],
        "users": {},
        "stats": {"total_views": 0, "total_users": 0}
    }

def save_db():
    # Нусхаи эҳтиётӣ (backup)
    if os.path.exists("data.json"):
        os.rename("data.json", f"data_backup_{datetime.now().strftime('%Y%m%d%H%M%S')}.json")
    
    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)

def is_subscribed(user_id):
    if not db["channels"]:  # Агар канал набошад
        return True
        
    for channel in db["channels"]:
        try:
            status = bot.get_chat_member(channel, user_id).status
            if status in ['member', 'administrator', 'creator']:
                continue
            else:
                return False
        except Exception as e:
            print(f"Error checking subscription: {e}")
            return False
    return True

def register_user(user):
    user_id = str(user.id)
    if user_id not in db["users"]:
        db["users"][user_id] = {
            "first_name": user.first_name,
            "last_name": user.last_name if user.last_name else "",
            "username": user.username if user.username else "",
            "joined_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "movies_watched": 0,
            "last_activity": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        db["stats"]["total_users"] += 1
        save_db()
    else:
        # Танҳо навсозии фаъолияти охирин
        db["users"][user_id]["last_activity"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        save_db()

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

# Ҳаракатҳои асосӣ
@bot.message_handler(commands=["start"])
def start(msg):
    register_user(msg.from_user)
    
    if is_subscribed(msg.chat.id):
        markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("🎬 Филмҳои нав", "🔎 Ҷустуҷӯи филм")
        markup.add("📊 Омори ман", "ℹ️ Дастурамал")
        
        bot.send_message(
            msg.chat.id, 
            f"Салом, {msg.from_user.first_name}! Хуш омадед ба Бот-и филмҳо.\n\n"
            "Барои гирифтани филм қулф-ID фиристед ё аз тугмаҳо истифода баред.",
            reply_markup=markup
        )
    else:
        markup = telebot.types.InlineKeyboardMarkup()
        for ch in db["channels"]:
            ch_name = ch.replace('@', '')
            try:
                chat_info = bot.get_chat(ch)
                title = chat_info.title
                markup.add(telebot.types.InlineKeyboardButton(f"📢 {title}", url=f"https://t.me/{ch_name}"))
            except:
                markup.add(telebot.types.InlineKeyboardButton(f"📢 {ch}", url=f"https://t.me/{ch_name}"))
                
        markup.add(telebot.types.InlineKeyboardButton("✅ Тафтиши обуна", callback_data="check_sub"))
        
        bot.send_message(
            msg.chat.id, 
            "⚠️ Барои истифодаи бот аввал ба каналҳои мо обуна шавед:",
            reply_markup=markup
        )

@bot.callback_query_handler(func=lambda call: call.data == "check_sub")
def check_sub(call):
    if is_subscribed(call.message.chat.id):
        # Тугмаҳо барои корбар
        markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("🎬 Филмҳои нав", "🔎 Ҷустуҷӯи филм")
        markup.add("📊 Омори ман", "ℹ️ Дастурамал")
        
        bot.edit_message_text(
            "✅ Офарин! Шумо ба ҳамаи каналҳо обуна шудед.\n\n"
            "Акнун метавонед аз бот истифода баред.",
            call.message.chat.id,
            call.message.message_id
        )
        
        bot.send_message(
            call.message.chat.id,
            "Барои гирифтани филм қулф-ID фиристед ё аз тугмаҳо истифода баред.",
            reply_markup=markup
        )
    else:
        bot.answer_callback_query(
            call.id,
            "❌ Шумо ҳанӯз обуна нашудаед. Лутфан, ба ҳамаи каналҳо обуна шавед!",
            show_alert=True
        )

# Панели администратор
@bot.message_handler(commands=["panel", "admin"])
def panel(msg):
    if msg.from_user.id == ADMIN_ID:
        markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("➕ Иловаи Филм", "➕ Иловаи Канал")
        markup.add("❌ Нест кардани Филм", "❌ Нест кардани Канал")
        markup.add("📊 Омор", "📋 Рӯйхати филмҳо")
        markup.add("🔄 Бот-ро аз нав сар кардан")
        
        bot.send_message(
            msg.chat.id, 
            "🔐 Панели администратор:\n\n"
            "Амалеро интихоб кунед:",
            reply_markup=markup
        )
    else:
        bot.send_message(msg.chat.id, "⛔ Шумо дастрасӣ надоред!")

# Иловаи филм
@bot.message_handler(func=lambda msg: msg.text == "➕ Иловаи Филм" and msg.from_user.id == ADMIN_ID)
def add_movie(msg):
    user_states[msg.chat.id] = "waiting_for_movie"
    
    # Тугмаи бекор кардан
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("🔙 Бекор кардан")
    
    bot.send_message(
        msg.chat.id, 
        "🎬 Лутфан, файли видеоро равон кунед:",
        reply_markup=markup
    )

# Иловаи канал
@bot.message_handler(func=lambda msg: msg.text == "➕ Иловаи Канал" and msg.from_user.id == ADMIN_ID)
def add_channel(msg):
    user_states[msg.chat.id] = "waiting_for_channel"
    
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("🔙 Бекор кардан")
    
    bot.send_message(
        msg.chat.id, 
        "📢 Номи каналро равон кунед (мисол: @kanal):",
        reply_markup=markup
    )

# Нест кардани филм
@bot.message_handler(func=lambda msg: msg.text == "❌ Нест кардани Филм" and msg.from_user.id == ADMIN_ID)
def delete_movie(msg):
    if db["movies"]:
        # Сохтани феҳрист бо тугмаҳо
        markup = telebot.types.InlineKeyboardMarkup()
        
        for movie_id, movie_data in db["movies"].items():
            # Номи филм ё ID
            movie_name = movie_data.get("title", f"Филм #{movie_id}")
            markup.add(telebot.types.InlineKeyboardButton(
                f"🎬 {movie_name} (ID: {movie_id})",
                callback_data=f"delete_movie_{movie_id}"
            ))
            
        markup.add(telebot.types.InlineKeyboardButton("🔙 Бекор кардан", callback_data="cancel_delete"))
        
        bot.send_message(
            msg.chat.id, 
            "❌ Филмро барои нест кардан интихоб кунед:",
            reply_markup=markup
        )
    else:
        bot.send_message(msg.chat.id, "❌ Ягон филм дар пойгоҳи додаҳо ёфт нашуд.")

# Обработчик для выбора фильма для удаления
@bot.callback_query_handler(func=lambda call: call.data.startswith("delete_movie_"))
def confirm_delete_movie(call):
    movie_id = call.data.split("_")[2]
    
    if movie_id in db["movies"]:
        movie_name = db["movies"][movie_id].get("title", f"Филм #{movie_id}")
        
        markup = telebot.types.InlineKeyboardMarkup()
        markup.add(
            telebot.types.InlineKeyboardButton("✅ Бале, нест кунед", callback_data=f"confirm_delete_{movie_id}"),
            telebot.types.InlineKeyboardButton("❌ Не", callback_data="cancel_delete")
        )
        
        bot.edit_message_text(
            f"🗑 Оё шумо дар ҳақиқат мехоҳед филми \"{movie_name}\" (ID: {movie_id})-ро нест кунед?",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=markup
        )
    else:
        bot.answer_callback_query(call.id, "❌ Филм ёфт нашуд!", show_alert=True)

# Подтверждение удаления фильма
@bot.callback_query_handler(func=lambda call: call.data.startswith("confirm_delete_"))
def process_delete_movie(call):
    movie_id = call.data.split("_")[2]
    
    if movie_id in db["movies"]:
        movie_name = db["movies"][movie_id].get("title", f"Филм #{movie_id}")
        db["movies"].pop(movie_id)
        save_db()
        
        bot.edit_message_text(
            f"✅ Филми \"{movie_name}\" (ID: {movie_id}) бо муваффақият нест карда шуд!",
            call.message.chat.id,
            call.message.message_id
        )
        
        # Возвращаем админ-панель
        panel(call.message)
    else:
        bot.answer_callback_query(call.id, "❌ Филм ёфт нашуд!", show_alert=True)
        
# Отмена удаления
@bot.callback_query_handler(func=lambda call: call.data == "cancel_delete")
def cancel_delete(call):
    bot.edit_message_text(
        "❌ Амалиёт бекор карда шуд!",
        call.message.chat.id,
        call.message.message_id
    )
    
    # Возвращаем админ-панель
    panel(call.message)

# Нест кардани канал
@bot.message_handler(func=lambda msg: msg.text == "❌ Нест кардани Канал" and msg.from_user.id == ADMIN_ID)
def delete_channel(msg):
    if db["channels"]:
        markup = telebot.types.InlineKeyboardMarkup()
        
        for i, ch in enumerate(db["channels"]):
            try:
                chat_info = bot.get_chat(ch)
                title = chat_info.title
                markup.add(telebot.types.InlineKeyboardButton(
                    f"📢 {title} ({ch})", 
                    callback_data=f"delete_channel_{i}"
                ))
            except:
                markup.add(telebot.types.InlineKeyboardButton(
                    f"📢 {ch}", 
                    callback_data=f"delete_channel_{i}"
                ))
                
        markup.add(telebot.types.InlineKeyboardButton("🔙 Бекор кардан", callback_data="cancel_delete"))
        
        bot.send_message(
            msg.chat.id, 
            "❌ Каналро барои нест кардан интихоб кунед:",
            reply_markup=markup
        )
    else:
        bot.send_message(msg.chat.id, "❌ Ягон канал дар пойгоҳи додаҳо ёфт нашуд.")

# Обработчик для удаления канала
@bot.callback_query_handler(func=lambda call: call.data.startswith("delete_channel_"))
def process_delete_channel(call):
    try:
        index = int(call.data.split("_")[2])
        
        if 0 <= index < len(db["channels"]):
            ch = db["channels"].pop(index)
            save_db()
            
            bot.edit_message_text(
                f"✅ Канали {ch} бо муваффақият нест карда шуд!",
                call.message.chat.id,
                call.message.message_id
            )
            
            # Возвращаем админ-панель
            panel(call.message)
        else:
            bot.answer_callback_query(call.id, "❌ Рақам нодуруст!", show_alert=True)
    except Exception as e:
        bot.answer_callback_query(call.id, f"❌ Хатогӣ: {e}", show_alert=True)

# Омори админ
@bot.message_handler(func=lambda msg: msg.text == "📊 Омор" and msg.from_user.id == ADMIN_ID)
def admin_stats(msg):
    total_users = db["stats"]["total_users"]
    total_views = db["stats"]["total_views"]
    total_movies = len(db["movies"])
    total_channels = len(db["channels"])
    
    # Аз поргоҳи маълумот ба даст овардани феҳрист
    active_users = 0
    for user_id, user_data in db["users"].items():
        # Ҳисоби корбарони фаъол дар ҳафтаи охир
        last_activity = datetime.strptime(user_data["last_activity"], "%Y-%m-%d %H:%M:%S")
        if (datetime.now() - last_activity).days < 7:
            active_users += 1
    
    bot.send_message(
        msg.chat.id,
        f"📊 *Омори бот:*\n\n"
        f"👥 *Корбарон:* {total_users}\n"
        f"👤 *Корбарони фаъол (7 рӯз):* {active_users}\n"
        f"🎬 *Шумораи филмҳо:* {total_movies}\n"
        f"📢 *Шумораи каналҳо:* {total_channels}\n"
        f"👁 *Ҳамагӣ тамошоҳо:* {total_views}",
        parse_mode="Markdown"
    )

# Рӯйхати филмҳо
@bot.message_handler(func=lambda msg: msg.text == "📋 Рӯйхати филмҳо" and msg.from_user.id == ADMIN_ID)
def movie_list(msg):
    if db["movies"]:
        message = "📋 *Рӯйхати филмҳои мавҷуда:*\n\n"
        
        for movie_id, movie_data in db["movies"].items():
            title = movie_data.get("title", "Бе ном")
            views = movie_data.get("views", 0)
            message += f"🎬 *{title}*\n"
            message += f"🔑 ID: `{movie_id}`\n"
            message += f"👁 Тамошоҳо: {views}\n\n"
            
            # Агар паём аз ҳад зиёд дароз шавад, равон кунад ва идома диҳад
            if len(message) > 3500:
                bot.send_message(msg.chat.id, message, parse_mode="Markdown")
                message = ""
        
        if message:
            bot.send_message(msg.chat.id, message, parse_mode="Markdown")
    else:
        bot.send_message(msg.chat.id, "❌ Ягон филм дар пойгоҳи додаҳо ёфт нашуд.")

# Бекор кардан
@bot.message_handler(func=lambda msg: msg.text == "🔙 Бекор кардан")
def cancel_operation(msg):
    if msg.from_user.id == ADMIN_ID:
        if msg.chat.id in user_states:
            user_states.pop(msg.chat.id)
        panel(msg)
    else:
        start(msg)

# Аз нав боркунии бот
@bot.message_handler(func=lambda msg: msg.text == "🔄 Бот-ро аз нав сар кардан" and msg.from_user.id == ADMIN_ID)
def restart_bot(msg):
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("✅ Тасдиқ", "❌ Бекор кардан")
    
    bot.send_message(
        msg.chat.id,
        "⚠️ Диққат! Бот-ро аз нав сар кардан мумкин аст.\n\n"
        "Оё шумо мехоҳед давом диҳед?",
        reply_markup=markup
    )
    
    user_states[msg.chat.id] = "confirm_restart"

@bot.message_handler(func=lambda msg: user_states.get(msg.chat.id) == "confirm_restart" and msg.from_user.id == ADMIN_ID)
def confirm_restart(msg):
    if msg.text == "✅ Тасдиқ":
        bot.send_message(msg.chat.id, "🔄 Бот аз нав сар карда мешавад...")
        # Сохранение всех данных
        save_db()
        # Возвращение к панели администратора
        panel(msg)
    else:
        bot.send_message(msg.chat.id, "❌ Амалиёт бекор карда шуд.")
        panel(msg)
    
    user_states.pop(msg.chat.id)

# Қабули файли видео аз админ
@bot.message_handler(content_types=["video"])
def save_movie(msg):
    if msg.from_user.id != ADMIN_ID:
        return
        
    if user_states.get(msg.chat.id) == "waiting_for_movie":
        # Дохил кардани маълумот дар бораи филм
        movie_id = str(random.randint(1000, 9999))
        
        # Тавлиди ID-и нав агар ID-и феъла мавҷуд бошад
        while movie_id in db["movies"]:
            movie_id = str(random.randint(1000, 9999))
        
        movie_info_temp[msg.chat.id] = {
            "id": movie_id,
            "file_id": msg.video.file_id,
            "file_size": msg.video.file_size,
            "duration": msg.video.duration,
            "width": msg.video.width,
            "height": msg.video.height
        }
        
        user_states[msg.chat.id] = "waiting_for_movie_title"
        
        markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("🔙 Бекор кардан")
        
        bot.send_message(
            msg.chat.id, 
            "📝 Номи филмро дохил кунед:",
            reply_markup=markup
        )

# Қабули номи филм
@bot.message_handler(func=lambda msg: user_states.get(msg.chat.id) == "waiting_for_movie_title")
def add_movie_title(msg):
    if msg.text == "🔙 Бекор кардан":
        if msg.chat.id in movie_info_temp:
            movie_info_temp.pop(msg.chat.id)
        user_states.pop(msg.chat.id)
        panel(msg)
        return
        
    movie_info_temp[msg.chat.id]["title"] = msg.text
    user_states[msg.chat.id] = "waiting_for_movie_info"
    
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("/skip")
    markup.add("🔙 Бекор кардан")
    
    bot.send_message(
        msg.chat.id, 
        "📋 Маълумоти филмро равон кунед ё /skip нависед:\n\n"
        "Мисол: Жанр, сол, режиссёр, актёрон ва ғайра",
        reply_markup=markup
    )

# Қабули маълумоти филм
@bot.message_handler(func=lambda msg: user_states.get(msg.chat.id) == "waiting_for_movie_info")
def add_movie_info(msg):
    if msg.text == "🔙 Бекор кардан":
        if msg.chat.id in movie_info_temp:
            movie_info_temp.pop(msg.chat.id)
        user_states.pop(msg.chat.id)
        panel(msg)
        return
    
    movie_info = "" if msg.text == "/skip" else msg.text
    movie_data = movie_info_temp[msg.chat.id]
    movie_id = movie_data["id"]
    
    # Сохтани объекти филм бо маълумоти пурра
    db["movies"][movie_id] = {
        "file_id": movie_data["file_id"],
        "title": movie_data["title"],
        "info": movie_info,
        "file_size": movie_data["file_size"],
        "duration": movie_data["duration"],
        "width": movie_data["width"],
        "height": movie_data["height"],
        "added_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "views": 0
    }
    
    save_db()
    
    # Нишон додани маълумот
    movie_size_mb = round(movie_data["file_size"] / (1024 * 1024), 2)
    duration_min = int(movie_data["duration"] / 60)
    duration_sec = movie_data["duration"] % 60
    
    user_states.pop(msg.chat.id)
    movie_info_temp.pop(msg.chat.id)
    
    bot.send_message(
        msg.chat.id, 
        f"✅ Филм бо муваффақият сабт шуд!\n\n"
        f"📌 *Номи филм:* {movie_data['title']}\n"
        f"🔑 *Қулф ID:* `{movie_id}`\n"
        f"⏱ *Давомнокӣ:* {duration_min}:{duration_sec:02d}\n"
        f"📊 *Ҳаҷм:* {movie_size_mb} MB\n"
        f"📋 *Маълумот:* {movie_info if movie_info else 'Нест'}",
        parse_mode="Markdown"
    )
    
    # Бозгашт ба панели асосӣ
    panel(msg)

# Қабули канал
@bot.message_handler(func=lambda msg: user_states.get(msg.chat.id) == "waiting_for_channel")
def save_channel(msg):
    if msg.text == "🔙 Бекор кардан":
        user_states.pop(msg.chat.id)
        panel(msg)
        return
    
    channel = msg.text
    
    # Агар @ надошта бошад, илова кунед
    if not channel.startswith('@'):
        channel = '@' + channel
    
    # Агар канал аллакай дар рӯйхат бошад
    if channel in db["channels"]:
        bot.send_message(msg.chat.id, f"⚠️ Канали {channel} аллакай дар рӯйхат мавҷуд аст!")
        user_states.pop(msg.chat.id)
        panel(msg)
        return
    
    # Санҷидани дуруст будани канал
    try:
        bot.get_chat(channel)
        db["channels"].append(channel)
        save_db()
        bot.send_message(msg.chat.id, f"✅ Канали {channel} бо муваффақият сабт шуд!")
    except Exception as e:
        bot.send_message(
            msg.chat.id, 
            f"❌ Хатогӣ ҳангоми илова кардани канал: {e}\n\n"
            f"Мутмаин шавед, ки канал мавҷуд аст ва бот дар он админ мебошад."
        )
    
    user_states.pop(msg.chat.id)
    panel(msg)

# Филмҳои нав
@bot.message_handler(func=lambda msg: msg.text == "🎬 Филмҳои нав")
def new_movies(msg):
    if not is_subscribed(msg.chat.id):
        start(msg)
        return
    
    if not db["movies"]:
        bot.send_message(msg.chat.id, "❌ Ҳоло ягон филм дар бот мавҷуд нест.")
        return
    
    # Мураттабсозии филмҳо аз рӯи сана
    sorted_movies = sorted(
        db["movies"].items(),
        key=lambda x: x[1].get("added_date", "2000-01-01"),
        reverse=True
    )
    
    # Нишон додани 5 филми охирин
    latest_movies = sorted_movies[:5]
    
    message = "🎬 *5 филми охирин:*\n\n"
    
    for movie_id, movie_data in latest_movies:
        title = movie_data.get("title", "Бе ном")
        views = movie_data.get("views", 0)
        date = movie_data.get("added_date", "Номаълум")
        
        message += f"🎬 *{title}*\n"
        message += f"🔑 ID: `{movie_id}`\n"
        message += f"📅 Илова шуд: {date[:10]}\n"
        message += f"👁 Тамошоҳо: {views}\n\n"
    
    message += "Барои дидани филм ID-ро нависед."
    
    bot.send_message(msg.chat.id, message, parse_mode="Markdown")

# Ҷустуҷӯи филм
@bot.message_handler(func=lambda msg: msg.text == "🔎 Ҷустуҷӯи филм")
def search_movie(msg):
    if not is_subscribed(msg.chat.id):
        start(msg)
        return
    
    user_states[msg.chat.id] = "waiting_for_search_query"
    
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("🔙 Бекор кардан")
    
    bot.send_message(
        msg.chat.id, 
        "🔎 Номи филмро барои ҷустуҷӯ дохил кунед:",
        reply_markup=markup
    )

# Коркарди ҷустуҷӯ
@bot.message_handler(func=lambda msg: user_states.get(msg.chat.id) == "waiting_for_search_query")
def process_search(msg):
    if msg.text == "🔙 Бекор кардан":
        user_states.pop(msg.chat.id)
        start(msg)
        return
    
    query = msg.text.lower()
    results = []
    
    for movie_id, movie_data in db["movies"].items():
        title = movie_data.get("title", "").lower()
        info = movie_data.get("info", "").lower()
        
        if query in title or query in info:
            results.append((movie_id, movie_data))
    
    if results:
        message = f"🔎 *Натиҷаҳои ҷустуҷӯ барои '{msg.text}'*:\n\n"
        
        for movie_id, movie_data in results[:10]:  # Танҳо 10 натиҷаи аввал
            title = movie_data.get("title", "Бе ном")
            views = movie_data.get("views", 0)
            
            message += f"🎬 *{title}*\n"
            message += f"🔑 ID: `{movie_id}`\n"
            message += f"👁 Тамошоҳо: {views}\n\n"
        
        if len(results) > 10:
            message += f"... ва боз {len(results) - 10} натиҷа.\n\n"
            
        message += "Барои дидани филм ID-ро нависед."
        
        bot.send_message(msg.chat.id, message, parse_mode="Markdown")
    else:
        bot.send_message(
            msg.chat.id, 
            f"❌ Ягон филм бо калимаи '{msg.text}' ёфт нашуд.\n\n"
            "Лутфан, бо калимаҳои дигар кӯшиш кунед."
        )
    
    user_states.pop(msg.chat.id)

# Омори ман
@bot.message_handler(func=lambda msg: msg.text == "📊 Омори ман")
def user_stats(msg):
    if not is_subscribed(msg.chat.id):
        start(msg)
        return
    
    user_id = str(msg.from_user.id)
    
    if user_id in db["users"]:
        user_data = db["users"][user_id]
        joined_date = user_data.get("joined_date", "Номаълум")
        movies_watched = user_data.get("movies_watched", 0)
        
        bot.send_message(
            msg.chat.id,
            f"📊 *Омори шумо:*\n\n"
            f"📅 *Аъзо шудаед аз:* {joined_date[:10]}\n"
            f"🎬 *Филмҳои тамошокарда:* {movies_watched}",
            parse_mode="Markdown"
        )
    else:
        bot.send_message(msg.chat.id, "❌ Маълумот дар бораи шумо ёфт нашуд.")

# Дастурамал
@bot.message_handler(func=lambda msg: msg.text == "ℹ️ Дастурамал")
def instructions(msg):
    if not is_subscribed(msg.chat.id):
        start(msg)
        return
    
    bot.send_message(
        msg.chat.id,
        "ℹ️ *Дастурамали истифодаи бот:*\n\n"
        "1️⃣ Барои пайдо кардани филм метавонед аз тугмаи 🔎 *Ҷустуҷӯи филм* истифода баред\n\n"
        "2️⃣ Барои дидани филмҳои нав аз тугмаи 🎬 *Филмҳои нав* истифода баред\n\n"
        "3️⃣ Агар ID-и филмро донед, онро бевосита ба бот нависед\n\n"
        "4️⃣ Барои дидани омори худ аз тугмаи 📊 *Омори ман* истифода баред",
        parse_mode="Markdown"
    )

# Қабули ID-и филм аз корбар
@bot.message_handler(func=lambda msg: len(msg.text) == 4 and msg.text.isdigit())
def get_movie_by_id(msg):
    if not is_subscribed(msg.chat.id):
        start(msg)
        return
    
    movie_id = msg.text
    
    if movie_id in db["movies"]:
        movie_data = db["movies"][movie_id]
        
        # Зиёд кардани шумораи тамошо
        db["movies"][movie_id]["views"] = movie_data.get("views", 0) + 1
        db["stats"]["total_views"] += 1
        
        # Навсозии омори корбар
        user_id = str(msg.from_user.id)
        if user_id in db["users"]:
            db["users"][user_id]["movies_watched"] = db["users"][user_id].get("movies_watched", 0) + 1
        
        save_db()
        
        # Тайёр кардани маълумот барои нишон додан
        title = movie_data.get("title", "Бе ном")
        info = movie_data.get("info", "Маълумот мавҷуд нест")
        file_id = movie_data.get("file_id")
        views = movie_data.get("views", 0)
        
        # Ҳисоб кардани давомнокӣ
        duration = movie_data.get("duration", 0)
        duration_min = int(duration / 60)
        duration_sec = duration % 60
        
        # Нишон додани филм
        caption = f"🎬 *{title}*\n\n"
        caption += f"⏱ *Давомнокӣ:* {duration_min}:{duration_sec:02d}\n"
        caption += f"👁 *Тамошоҳо:* {views}\n\n"
        caption += f"📝 *Маълумот:*\n{info}"
        
        try:
            bot.send_video(
                msg.chat.id,
                file_id,
                caption=caption,
                parse_mode="Markdown"
            )
        except Exception as e:
            bot.send_message(
                msg.chat.id,
                f"❌ Хатогӣ ҳангоми фиристодани видео: {e}"
            )
    else:
        bot.send_message(
            msg.chat.id,
            f"❌ Филм бо ID {movie_id} ёфт нашуд.\n\n"
            "Лутфан, ID-ро санҷед ва аз нав кӯшиш кунед."
        )

# Барои дигар паёмҳо
@bot.message_handler(func=lambda msg: True)
def default_handler(msg):
    if not is_subscribed(msg.chat.id):
        start(msg)
        return
    
    bot.send_message(
        msg.chat.id,
        "❓ Лутфан, аз тугмаҳои зерин истифода баред ё ID-и филмро нависед."
    )
    # Webhook-ро насб мекунем
bot.remove_webhook()
bot.set_webhook(url=f"https://main-bot-7ydv.onrender.com/7105177180:AAGvw_qqid-VIVMwGMZIbo3L6cZCYQgj2DY")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
