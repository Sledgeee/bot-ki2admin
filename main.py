from datetime import datetime

import pytz

import db
from bot import bot, HEARTBEAT_CHAT_ID
from fastapi import FastAPI, Request, status
from telebot.types import Update


app = FastAPI()


@app.post("/webhook/bot")
async def webhook(req: Request):
    if req.headers.get('content-type') == 'application/json':
        json_string = await req.json()
        update = Update.de_json(json_string)
        bot.process_new_updates([update])
        return ''
    else:
        return status.HTTP_403_FORBIDDEN


@app.post("/ping")
async def ping():
    last_ping = db.health.get("admin")

    def update_health():
        db.health.put({
            "last_message_id": msg.message_id,
            "last_update": str(datetime.now(tz=pytz.timezone("Europe/Kiev")))
        }, "admin")

    if last_ping:
        bot.delete_message(HEARTBEAT_CHAT_ID, last_ping["last_message_id"])
    try:
        msg = bot.send_message(HEARTBEAT_CHAT_ID, "pong")
        if msg is not None:
            update_health()
    except:
        pass
