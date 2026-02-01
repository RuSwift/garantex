from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from routers import auth
from web3_auth import web3_auth

app = FastAPI(
    title="RuSwift DApp Node API",
    description="Decentralized financial marketplace",
    version="1.0.0"
)

# Настройка Jinja2 шаблонов
templates = Jinja2Templates(directory="templates")

# Настройка статических файлов
app.mount("/static", StaticFiles(directory="static"), name="static")

# Настройка CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # В продакшене указать конкретные домены
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключение роутеров
app.include_router(auth.router)


@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """
    Главная страница с админ-панелью
    """
    # Проверяем наличие токена в cookies
    token = request.cookies.get("auth_token")
    user_info = None
    
    if token:
        try:
            # Проверяем токен и получаем информацию о пользователе
            payload = web3_auth.verify_jwt_token(token)
            wallet_address = payload.get("wallet_address")
            if wallet_address:
                user_info = {"wallet_address": wallet_address}
        except Exception:
            # Если токен невалиден, игнорируем ошибку
            user_info = None
    
    # Боковое меню
    side_menu = [
        {
            "header": "Инструменты",
            "items": [
                {
                    "id": "dashboard",
                    "href": "/",
                    "icon_class": "fas fa-tachometer-alt",
                    "label": "Дашборд",
                    "sub": [],
                    "page": "Dashboard"
                }
            ]
        },
        {
            "header": "Аккаунт",
            "items": [
                {
                    "id": "profile",
                    "href": "/profile",
                    "icon_class": "fa-regular fa-address-card",
                    "label": "Профиль",
                    "sub": [],
                    "page": "Profile"
                }
            ]
        }
    ]
    
    return templates.TemplateResponse(
        "panel.html",
        {
            "request": request,
            "app_name": "RuSwift DApp Node",
            "user": user_info,
            "side_menu": side_menu,
            "selected_menu": "dashboard",
            "current_page": "Dashboard",
            "labels": {}
        }
    )


@app.get("/health")
async def health_check():
    """Проверка здоровья приложения"""
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

