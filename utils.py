import base64
import os

import requests
from bot import bot, ADMIN_BOT_TOKEN


API_URL = "https://ki2helper.deta.dev/col"
AUTH_HEADER = os.getenv("AUTH_HEADER")


def api_request(method: str, path: str, token: str):
    response = requests.request(
        method,
        url=f"{API_URL}/{path}",
        headers={
            AUTH_HEADER: token
        }
    )
    return response.json()


def get_user_photo(user_id):
    photos = requests.get(url=f"https://api.telegram.org/bot{ADMIN_BOT_TOKEN}/getUserProfilePhotos", params={
        "user_id": user_id
    })
    res = dict(photos.json())
    if res["ok"] is True and res["result"]["total_count"] > 0:
        target_url = bot.get_file_url(res["result"]["photos"][0][0]["file_id"])
        prefix = "data:image/jpeg;base64,"
        bytes_ = (base64.b64encode(requests.get(target_url).content)).decode()
        return prefix + bytes_
    else:
        return "/static/img/pic.png"
