from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from routers import auth
from routers import didcomm
from dependencies import UserDepends, SettingsDepends, PrivKeyDepends, DbDepends
from schemas.node import NodeInitRequest, NodeInitPemRequest, NodeInitResponse
from didcomm.did import create_peer_did_from_keypair
from services.node import NodeService


app = FastAPI(
    title="Self-Hosted API",
    description="Decentralized financial marketplace",
    version="1.0.0"
)


@app.on_event("startup")
async def startup_event():
    """Инициализация при запуске приложения"""
    from db import init_db
    from settings import Settings
    
    # Инициализируем базу данных
    settings = Settings()
    init_db(settings.database)

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
app.include_router(didcomm.router)


@app.get("/", response_class=HTMLResponse)
async def root(
    request: Request,
    user_info: UserDepends,
    settings: SettingsDepends,
    db: DbDepends,
):
    """
    Главная страница с админ-панелью
    """
    
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
    
    # Проверяем инициализацию ноды из базы данных
    is_node_initialized = await NodeService.is_node_initialized(db)
    
    return templates.TemplateResponse(
        "panel.html",
        {
            "request": request,
            "app_name": "Self-Hosted Node",
            "user": user_info,
            "side_menu": side_menu,
            "selected_menu": "dashboard",
            "current_page": "Dashboard",
            "labels": {},
            "is_node_initialized": is_node_initialized
        }
    )


@app.get("/health")
async def health_check():
    """Проверка здоровья приложения"""
    from datetime import datetime, timezone
    return {
        "status": "ok",
        "utc": datetime.now(timezone.utc).isoformat()
    }


# API для инициализации ноды
@app.post("/api/node/init", response_model=NodeInitResponse)
async def init_node(
    request: NodeInitRequest,
    db: DbDepends,
    settings: SettingsDepends
):
    """
    Инициализирует ноду с использованием мнемонической фразы
    
    Args:
        request: Запрос с мнемонической фразой
        db: Database session
        settings: Настройки приложения
        
    Returns:
        Информация о созданном ключе ноды
    """
    # Проверяем что SECRET установлен
    if not settings.secret.get_secret_value():
        raise HTTPException(
            status_code=500,
            detail="SECRET not configured in environment variables"
        )
    
    try:
        # Вызываем сервис инициализации
        result = await NodeService.init_from_mnemonic(
            request.mnemonic,
            db,
            settings.secret.get_secret_value()
        )
        
        return NodeInitResponse(
            success=True,
            message="Node initialized successfully",
            **result
        )
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid mnemonic: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error initializing node: {str(e)}"
        )


@app.post("/api/node/init-pem", response_model=NodeInitResponse)
async def init_node_from_pem(
    request: NodeInitPemRequest,
    db: DbDepends,
    settings: SettingsDepends
):
    """
    Инициализирует ноду с использованием PEM ключа
    
    Args:
        request: Запрос с PEM данными и опциональным паролем
        db: Database session
        settings: Настройки приложения
        
    Returns:
        Информация о созданном ключе ноды
    """
    # Проверяем что SECRET установлен
    if not settings.secret.get_secret_value():
        raise HTTPException(
            status_code=500,
            detail="SECRET not configured in environment variables"
        )
    
    try:
        # Вызываем сервис инициализации
        result = await NodeService.init_from_pem(
            request.pem_data,
            request.password,
            db,
            settings.secret.get_secret_value()
        )
        
        return NodeInitResponse(
            success=True,
            message="Node initialized successfully",
            **result
        )
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid PEM data: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error initializing node: {str(e)}"
        )


@app.get("/api/node/key-info")
async def get_key_info(
    settings: SettingsDepends,
    priv_key: PrivKeyDepends,
    db: DbDepends
):
    """
    Получить информацию о ключе ноды, включая DID и DIDDoc
    """
    # Проверяем инициализацию ноды из базы данных
    is_initialized = await NodeService.is_node_initialized(db)
    if not is_initialized:
        raise HTTPException(status_code=404, detail="Нода не инициализирована")
    
    if priv_key is None:
        raise HTTPException(status_code=404, detail="Ключ не найден")
    
    # Получаем публичный ключ в разных форматах
    public_key_hex = priv_key.public_key.hex()
    
    # Получаем PEM публичного ключа
    if hasattr(priv_key, 'to_public_pem'):
        public_key_pem = priv_key.to_public_pem().decode('utf-8')
    else:
        # Для EthKeyPair используем базовый метод через _public_key_obj
        from cryptography.hazmat.primitives import serialization
        public_key_pem = priv_key._public_key_obj.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ).decode('utf-8')
    
    # Определяем тип ключа
    key_type = priv_key.key_type if hasattr(priv_key, 'key_type') else 'Unknown'
    
    # Получаем адрес (если это Ethereum ключ)
    address = None
    if hasattr(priv_key, 'address'):
        address = priv_key.address
    
    # Создаем DID из ключа
    did_obj = create_peer_did_from_keypair(priv_key)
    did = did_obj.did
    did_document = did_obj.to_dict()
    
    return {
        "address": address,
        "key_type": key_type,
        "public_key": public_key_hex,
        "public_key_pem": public_key_pem,
        "did": did,
        "did_document": did_document
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

