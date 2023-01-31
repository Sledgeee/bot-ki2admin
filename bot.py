import os
from typing import Union

import db
from telebot import TeleBot
from telebot.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, BotCommand, User
from utils import api_request

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
    is_admin = True if api_request('get', f'admins/has-rights/{user_id}')['result'] else False
    if is_admin:
        api_request('post', 'auth/cml', json={
            "user_id": int(user_id),
            "username": from_user.username,
            "is_magic": True
        })
    else:
        bot.send_message(from_user.id, "У вас немає прав адміністратора ❌")


@bot.message_handler(commands=["login"])
def login_cmd(message: Message):
    user = message.from_user
    login(user)


def get_admin_account(from_user: User):
    if api_request('get', f'admins/has-rights/{from_user.id}')['result']:
        bot.send_message(from_user.id, "Ви вже маєте права адміністратора ⚠️")
        return

    if db.get_admin_requests.get(str(from_user.id)) is not None:
        bot.send_message(from_user.id, "Ви вже зробили запит на отримання прав адміністратора ⚠️")
        return
    db.get_admin_requests.put({"username": from_user.username}, str(from_user.id))
    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("Одобрити ✅", callback_data=f"aa_{from_user.id}"),
        InlineKeyboardButton("Відхилити ❌", callback_data=f"da_{from_user.id}")
    )
    bot.send_message(OWNER_ID, f"Користувач @{from_user.username} зробив заявку на реєстрацію адмін-аккаунту:",
                     reply_markup=markup)
    bot.send_message(from_user.id,
                     "Запит на реєстрацію створено, очікуйте на відповідь ⏳")


def handle_get_admin_account_accepted(user_id: Union[str, int]):
    db.get_admin_requests.delete(str(user_id))
    msg = bot.send_message(user_id,
                           "Ваш запит на отримання прав адміністратора схвалено ✅\n"
                           "Придумайте логін для вашого аккаунта, я буду очікувати на вашу відповідь...")
    bot.register_next_step_handler(msg, handle_username_typed)


def handle_username_typed(message: Message):
    username = message.text
    if username.isalnum() and username.isascii():
        response = api_request('post', 'auth/register', json={
            "user_id": int(message.chat.id),
            "username": username
        })
        if "detail" in response:
            bot.send_message(message.chat.id, 'Цей логін вже існує, спробуйте інший')
            bot.register_next_step_handler(message, handle_username_typed)
        else:
            bot.send_message(message.chat.id, 'Аккаунт успішно створено ✅')
    else:
        bot.send_message(message.chat.id, 'Ви ввели некорректний логін, він може містити тільки англ. літери та цифри.'
                                          'Спробуйте ще раз, я буду очікувати на вашу відповідь...')
        bot.register_next_step_handler(message, handle_username_typed)


@bot.message_handler(commands=["register"])
def get_admin_role_cmd(message: Message):
    user = message.from_user
    get_admin_account(user)


def panel(from_user: User):
    bot.send_message(from_user.id, "https://ki2helper.pp.ua/", disable_web_page_preview=True)


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
        get_admin_account(call.from_user)
    elif "aa_" in call.data:
        user_id = call.data.split("_")[1]
        handle_get_admin_account_accepted(user_id)
    elif "da_" in call.data:
        user_id = call.data.split("_")[1]
        db.get_admin_requests.delete(user_id)
        bot.send_message(user_id, "Ваш запит на отримання прав адміністратора відхилено ❌")
    bot.delete_message(call.message.chat.id, call.message.message_id)


admin_commands = [
    BotCommand("/start", "Розпочати діалог з ботом"),
    BotCommand("/register", "Створити адмін-аккаунт"),
    BotCommand("/panel", "Отримати посилання на панель"),
    BotCommand("/login", "Авторизуватись в панель через магічне посилання")
]
bot.set_my_commands(commands=admin_commands)
