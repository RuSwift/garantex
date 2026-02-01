from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from routers import auth
from web3_auth import web3_auth

app = FastAPI(
    title="Garantex API",
    description="FastAPI приложение с Web3 авторизацией",
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
    Главная страница с интерфейсом авторизации Web3
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
    
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "user": user_info,
            "is_authenticated": user_info is not None
        }
    )


@app.get("/chat", response_class=HTMLResponse)
async def chat(request: Request):
    """
    Страница AI чата
    """
    return templates.TemplateResponse(
        "chat.html",
        {
            "request": request
        }
    )
    
    
@app.get("/seed", response_class=HTMLResponse)
async def seed(request: Request):
    """
    Создание криптографического ключа
    """
    return templates.TemplateResponse(
        "seed.html",
        {
            "request": request
        }
    )


@app.get("/health")
async def health_check():
    """Проверка здоровья приложения"""
    return {"status": "ok"}


@app.post("/logout")
async def logout():
    """
    Выход из системы - удаляет токен из cookies
    """
    response = RedirectResponse(url="/", status_code=303)
    response.delete_cookie("auth_token")
    return response


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

