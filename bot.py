import os
import uuid
import db
from datetime import datetime, timedelta
from telebot import TeleBot
from telebot.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, BotCommand, User
from security import JwtPayload, create_access_token

ADMIN_BOT_TOKEN = os.getenv("ADMIN_BOT_TOKEN")
OWNER_ID = os.getenv("OWNER_ID")
HEARTBEAT_CHAT_ID = os.getenv("HEARTBEAT_CHAT_ID")
bot = TeleBot(ADMIN_BOT_TOKEN, threaded=False)


@bot.message_handler(commands=['start'])
def start_cmd(message: Message):
    markup = InlineKeyboardMarkup()
    markup.row(InlineKeyboardButton("Авторизуватись в адмін-панель", callback_data="login"))
    markup.row(InlineKeyboardButton("Отримати посилання на адмін-панель", callback_data="panel"))
    markup.row(InlineKeyboardButton("Зробити запит на отримання прав адміна", callback_data="get_admin"))
    bot.send_message(message.chat.id, "Привіт, обирай, що потрібно:", reply_markup=markup)


def login(from_user: User):
    user_id = str(from_user.id)
    role = "Адміністратор"
    if user_id == OWNER_ID:
        is_admin = True
        role = "Власник"
    else:
        is_admin = True if db.admins.get(user_id) is not None else False

    if is_admin:
        existing_hash = db.temp_hashes.get(user_id)
        if existing_hash is not None:
            db.temp_hashes.delete(existing_hash["key"])

        payload = JwtPayload(
            sub=user_id,
            username=from_user.username,
            first_name=from_user.first_name,
            last_name=from_user.last_name,
            role=role
        )
        uuid4 = uuid.uuid4().hex
        access_token = create_access_token(payload)
        db.sessions.put({"token": access_token}, user_id)
        msg = bot.send_message(from_user.id,
                               "Для авторизації в панель "
                               "використайте посилання нижче (воно дійсне протягом 5 хвилин):\n"
                               f"https://ki2admin.deta.dev/login?user_id={user_id}&hash={uuid4}",
                               protect_content=True,
                               disable_web_page_preview=True)
        db.temp_hashes.put({
            "hash": uuid4,
            "message_id": msg.message_id,
            "__expires": int((datetime.utcnow() + timedelta(seconds=300)).timestamp())
        }, key=user_id)
    else:
        bot.send_message(from_user.id, "У вас немає прав адміністратора ❌")


@bot.message_handler(commands=["login"])
def login_cmd(message: Message):
    user = message.from_user
    login(user)


def get_admin_role(from_user: User):
    req = db.get_admin_requests.get(str(from_user.id))
    if req is not None:
        bot.send_message(from_user.id, "Ви вже зробили запит на отримання прав адміністратора ⚠️")
    else:
        db.get_admin_requests.insert({"user_id": from_user.id}, str(from_user.id))
        markup = InlineKeyboardMarkup()
        markup.row(
            InlineKeyboardButton("Одобрити ✅", callback_data=f"accept-admin_{from_user.id}"),
            InlineKeyboardButton("Відхилити ❌", callback_data=f"decline-admin_{from_user.id}")
        )
        bot.send_message(OWNER_ID, f"Користувач @{from_user.username} хоче отримати доступ адміністратора:",
                         reply_markup=markup)
        bot.send_message(from_user.id,
                         "Запит на отримання прав адміністратора створено, очікуйте на відповідь ⏳")


@bot.message_handler(commands=["get_admin_role"])
def get_admin_role_cmd(message: Message):
    user = message.from_user
    get_admin_role(user)


def panel(from_user: User):
    bot.send_message(from_user.id, "https://ki2admin.deta.dev/", disable_web_page_preview=True)


@bot.message_handler(commands=["panel"])
def panel_cmd(message: Message):
    user = message.from_user
    panel(user)


@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call: CallbackQuery):
    if call.data == "login":
        login(call.from_user)
    elif call.data == "panel":
        panel(call.from_user)
    elif call.data == "get_admin":
        get_admin_role(call.from_user)
    elif "accept-admin_" in call.data:
        user_id = call.data.split("_")[1]
        db.get_admin_requests.delete(user_id)
        db.admins.put({"super": False}, user_id)
        bot.send_message(user_id, "Ваш запит на отримання прав адміністратора схвалено ✅")
    elif "decline-admin_" in call.data:
        user_id = call.data.split("_")[1]
        db.get_admin_requests.delete(user_id)
        bot.send_message(user_id, "Ваш запит на отримання прав адміністратора відхилено ❌")
    bot.delete_message(call.message.chat.id, call.message.message_id)


admin_commands = [
    BotCommand("/start", "Розпочати діалог з ботом"),
    BotCommand("/get_admin_role", "Отримати роль адміністратора"),
    BotCommand("/panel", "Отримати посилання на адмін-панель"),
    BotCommand("/login", "Авторизуватись в адмін панель")
]
bot.set_my_commands(commands=admin_commands)
