from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from routers import auth
from dependencies import UserDepends

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
async def root(
    request: Request,
    user_info: UserDepends
):
    """
    Главная страница с интерфейсом авторизации Web3
    """
    
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


@app.get("/web3-auth-test", response_class=HTMLResponse)
async def web3_auth_test(request: Request):
    """
    Тестовая страница для компонента Web3Auth
    """
    return templates.TemplateResponse(
        "web3-auth-test.html",
        {
            "request": request
        }
    )


@app.get("/health")
async def health_check():
    """Проверка здоровья приложения"""
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

