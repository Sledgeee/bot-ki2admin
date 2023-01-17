import db
from bot import bot
from fastapi import FastAPI, Request, status, HTTPException, BackgroundTasks
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse, HTMLResponse
from telebot.types import Update
from security import raise_unauthorized, get_user, get_token, response_with_cookies
from utils import get_user_photo, api_request


app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    token = request.cookies.get("ACCESS_TOKEN")
    user = get_user(token)
    user["pic"] = get_user_photo(int(user["sub"]))
    context = {
        "request": request,
        "user": user,
        "data": {
            "cron": (api_request("get", "apps", token))[0]["cron"]
        },
        "tabs": [
            {"name": "Крон", "id": "cron"},
            {"name": "Дні народження", "id": "birthdays"},
            {"name": "Предмети", "id": "lessons"},
            {"name": "Викладачі", "id": "teachers"},
            {"name": "Розклад", "id": "schedule"},
            {"name": "Графік пар", "id": "timetable"},
            {"name": "Тиждень", "id": "week"},
            {"name": "Zoom", "id": "zoom"}
        ]
    }
    return templates.TemplateResponse("index.html", context=context)


@app.get("/login")
async def login(request: Request, background_tasks: BackgroundTasks):
    user_id = request.query_params.get("user_id")
    hash_ = request.query_params.get("hash")
    hash_item = db.temp_hashes.get(user_id)
    if hash_item["hash"] != hash_:
        raise_unauthorized()
    else:
        background_tasks.add_task(db.temp_hashes.delete, hash_item["key"])
        background_tasks.add_task(bot.delete_message, user_id, hash_item["message_id"])

    token = get_token(user_id)
    if token is not None:
        background_tasks.add_task(bot.send_message, user_id, "Ви були успішно авторизовані ✅")
        response = RedirectResponse("/")
        return response_with_cookies(token, response)
    raise_unauthorized()


@app.middleware("http")
async def process_requests(request: Request, call_next):
    response = await call_next(request)
    token = request.cookies.get("ACCESS_TOKEN")
    if token is not None:
        response = response_with_cookies(token, response)
    return response


@app.exception_handler(HTTPException)
async def handle_exception(request: Request, exc: HTTPException):
    context = {
        "request": request,
        "status_code": exc.status_code,
        "detail": exc.detail
    }
    return HTMLResponse(content=templates.TemplateResponse("error.html", context=context).body)


@app.post("/webhook/bot")
async def webhook(req: Request):
    if req.headers.get('content-type') == 'application/json':
        json_string = await req.json()
        update = Update.de_json(json_string)
        bot.process_new_updates([update])
        return ''
    else:
        return status.HTTP_403_FORBIDDEN


@app.on_event("shutdown")
def shutdown_event():
    db.client.close()
