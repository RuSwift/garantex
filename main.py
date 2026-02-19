from contextlib import asynccontextmanager
import asyncio
import logging
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
from routers.payment_request import router as payment_request_router
from dependencies import UserDepends
from settings import Settings
from db import init_db
from cron import cron_task

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Инициализация настроек и базы данных
settings = Settings()
init_db(settings.database)


async def run_cron_periodically():
    """
    Фоновая задача для периодического выполнения cron задач
    Выполняется каждые 5 секунд
    Перезапускается автоматически после падения
    """
    while True:
        try:
            print("Cron task execution started")
            await cron_task()
            print("Cron task execution completed")
        except Exception as e:
            # Логируем ошибку, но продолжаем работу
            print(f"Error in cron task: {str(e)}")
            print("Cron task will continue after 5 seconds...")
        except BaseException as e:
            # Обрабатываем критические ошибки (включая KeyboardInterrupt, SystemExit)
            print(f"Critical error in cron task: {str(e)}")
            print("Restarting cron task in 5 seconds...")
        await asyncio.sleep(5)  # Ждем 5 секунд перед следующим вызовом


async def run_cron_with_restart():
    """
    Обертка для запуска cron задачи с автоматическим перезапуском при падении
    """
    while True:
        try:
            await run_cron_periodically()
        except Exception as e:
            print(f"Cron task crashed: {str(e)}")
            print("Restarting cron task in 5 seconds...")
            await asyncio.sleep(5)
        except BaseException as e:
            print(f"Critical error in cron wrapper: {str(e)}")
            print("Restarting cron task in 5 seconds...")
            await asyncio.sleep(5)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager для FastAPI app
    Выполняет код при старте и остановке приложения
    """
    # Startup: запускаем фоновую задачу для cron с автоматическим перезапуском
    cron_task_handle = asyncio.create_task(run_cron_with_restart())
    
    yield
    
    # Shutdown: останавливаем фоновую задачу
    cron_task_handle.cancel()
    try:
        await cron_task_handle
    except asyncio.CancelledError:
        pass


app = FastAPI(
    title="Garantex API",
    description="FastAPI приложение с Web3 авторизацией",
    version="1.0.0",
    lifespan=lifespan
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
app.include_router(payment_request_router)


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


@app.get("/test-chat", response_class=HTMLResponse)
async def test_chat(request: Request):
    """
    Тестовая страница для компонента Chat с профилем собеседника из URL
    
    Параметры:
    - did: DID контрагента (обязательный URL-параметр)
    """
    return templates.TemplateResponse(
        "test-chat.html",
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


@app.get("/deal/{deal_uid}", response_class=HTMLResponse)
async def deal_page(
    deal_uid: str,
    request: Request,
    user_info: UserDepends
):
    """
    Страница сделки
    
    Args:
        deal_uid: UID сделки (base58 UUID)
        request: Request object
        user_info: User info from dependency
    """
    return templates.TemplateResponse(
        "deal.html",
        {
            "request": request,
            "user": user_info,
            "is_authenticated": user_info is not None,
            "app_name": "Гильдия",
            "deal_uid": deal_uid
        }
    )


@app.get("/health")
async def health_check():
    """Проверка здоровья приложения"""
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

