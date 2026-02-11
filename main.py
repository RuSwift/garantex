from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from routers import auth
from routers import tron_multisig
from routers.wallet_users import profile_router, router as wallet_users_router
from routers.advertisements import marketplace_router, my_ads_router, admin_ads_router
from routers.billing import router as billing_router
from routers.chat import router as chat_router
from dependencies import UserDepends
from settings import Settings
from db import init_db

# Инициализация настроек и базы данных
settings = Settings()
init_db(settings.database)

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
app.include_router(tron_multisig.router)
app.include_router(profile_router)
app.include_router(wallet_users_router)
app.include_router(marketplace_router)
app.include_router(my_ads_router)
app.include_router(admin_ads_router)
app.include_router(billing_router)
app.include_router(chat_router)


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
            "is_authenticated": user_info is not None,
            "app_name": "Гильдия",
            "app_description": "Децентрализованная платформа для проведения трансгран-платежей. Подключите кошелек TRON для входа.",
            "app_tagline": "DEX Platform"
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


@app.get("/web3-auth-mobile-test", response_class=HTMLResponse)
async def web3_auth_mobile_test(request: Request):
    """
    Тестовая страница для мобильного компонента Web3AuthMobile
    """
    return templates.TemplateResponse(
        "web3-auth-mobile-test.html",
        {
            "request": request
        }
    )


@app.get("/tron-auth-test", response_class=HTMLResponse)
async def tron_auth_test(request: Request):
    """
    Тестовая страница для компонента TronAuth
    
    Поддерживает авторизацию через TRON кошельки:
    - TronLink (desktop)
    - TrustWallet (desktop + mobile)
    - WalletConnect (mobile)
    """
    return templates.TemplateResponse(
        "tron-auth-test.html",
        {
            "request": request
        }
    )


@app.get("/tron-multisig-test", response_class=HTMLResponse)
async def tron_multisig_test(request: Request):
    """
    Тестовая страница для TRON Multisig
    
    Демонстрирует работу мультиподписного кошелька 2/3:
    - Создание конфигурации N/M
    - Подпись через TronLink
    - Автоматическая подпись остальными участниками
    - Валидация и финализация транзакции
    """
    return templates.TemplateResponse(
        "tron-multisig-test.html",
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

