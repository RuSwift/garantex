from fastapi import FastAPI, Request, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from routers import auth
from routers import didcomm
from routers import wallet_users
from routers.billing import router as billing_router
from routers import wallets
from routers import admin
from routers.chat import router as chat_router
from dependencies import UserDepends, AdminDepends, RequireAdminDepends, SettingsDepends, PrivKeyDepends, DbDepends, get_admin_from_cookie
from schemas.node import (
    NodeInitRequest, NodeInitPemRequest, NodeInitResponse,
    AdminConfiguredResponse,
    ChangeResponse,
    SetServiceEndpointRequest, ServiceEndpointResponse, 
    TestServiceEndpointRequest, TestServiceEndpointResponse
)
from didcomm.did import create_peer_did_from_keypair
from services.node import NodeService
from services.admin import AdminService


app = FastAPI(
    title="Self-Hosted API",
    description="Decentralized financial marketplace",
    version="1.0.0"
)


@app.on_event("startup")
async def startup_event():
    """Инициализация при запуске приложения"""
    from db import init_db, SessionLocal
    from settings import Settings
    
    # Инициализируем базу данных
    settings = Settings()
    init_db(settings.database)
    
    # Инициализируем админа из env vars если настроен
    # ENV VARS имеют приоритет над БД
    if settings.admin.is_configured:
        async with SessionLocal() as session:
            await AdminService.init_from_env(settings.admin, session)

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
app.include_router(wallet_users.profile_router)
app.include_router(wallet_users.router)
app.include_router(billing_router)
app.include_router(wallets.router)
app.include_router(admin.router)
app.include_router(chat_router)


@app.get("/tron-sign-test", response_class=HTMLResponse)
async def tron_sign_test(request: Request):
    """Тестовая страница для компонента TronSign"""
    return templates.TemplateResponse("tron-sign-test.html", {"request": request})


@app.get("/", response_class=HTMLResponse)
async def root(
    request: Request,
    user_info: UserDepends,
    admin_info: AdminDepends,
    settings: SettingsDepends,
    db: DbDepends,
):
    """
    Главная страница с админ-панелью
    
    Требует авторизации админа для доступа к панели управления нодой
    """
    
    # Проверяем инициализацию ноды из базы данных
    is_node_initialized = await NodeService.is_node_initialized(db)
    
    # Если нода проинициализирована, требуем авторизацию админа
    if is_node_initialized:
        if not admin_info:
            # Пользователь не авторизован как админ - показываем страницу входа
            return templates.TemplateResponse(
                "node/login.html",
                {
                    "request": request
                }
            )
    
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
            "header": "Маркетплейс",
            "items": [
                {
                    "id": "wallet-users",
                    "href": "/wallet-users",
                    "icon_class": "fas fa-users",
                    "label": "Пользователи",
                    "sub": [],
                    "page": "WalletUsers"
                }
            ]
        },
        {
            "header": "Администратор",
            "items": [
                {
                    "id": "wallets",
                    "href": "/",
                    "icon_class": "fas fa-tachometer-alt",
                    "label": "Кошельки",
                    "sub": [],
                    "page": "Wallets"
                },
                {
                    "id": "profile",
                    "href": "/profile",
                    "icon_class": "fa-regular fa-address-card",
                    "label": "Нода",
                    "sub": [],
                    "page": "Profile"
                },
                {
                    "id": "admin-account",
                    "href": "/admin-account",
                    "icon_class": "fas fa-user-shield",
                    "label": "Админ",
                    "sub": [],
                    "page": "AdminAccount"
                }
            ]
        }
    ]
    
    return templates.TemplateResponse(
        "panel.html",
        {
            "request": request,
            "app_name": "Self-Hosted Node",
            "user": user_info,
            "admin": admin_info,
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
    request: Request,
    data: NodeInitRequest,
    db: DbDepends,
    settings: SettingsDepends,
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
        
    admin = await get_admin_from_cookie(request, settings)
    node_initialized = await NodeService.is_node_initialized(db)
    if node_initialized and not admin:
        raise HTTPException(
            status_code=401,
            detail="Node already initialized, please login as admin"
        )
    
    try:
        # Вызываем сервис инициализации
        result = await NodeService.init_from_mnemonic(
            data.mnemonic,
            db,
            settings.secret.get_secret_value()
        )
        
        # Проверяем, что запись действительно создалась в БД
        if not await NodeService.has_key(db):
            raise HTTPException(
                status_code=500,
                detail="Failed to create NodeSettings record in database"
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
    settings: SettingsDepends,
    admin: RequireAdminDepends
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
        
        # Проверяем, что запись действительно создалась в БД
        if not await NodeService.has_key(db):
            raise HTTPException(
                status_code=500,
                detail="Failed to create NodeSettings record in database"
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
    db: DbDepends,
    admin: RequireAdminDepends
):
    """
    Получить информацию о ключе ноды, включая DID и DIDDoc
    """
    # Проверяем наличие ключа ноды
    has_key = await NodeService.has_key(db)
    if not has_key:
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
    
    # Получаем service_endpoint из базы данных
    service_endpoint = await NodeService.get_service_endpoint(db)
    
    # Создаем service endpoints для DID если они настроены
    service_endpoints = None
    if service_endpoint:
        from didcomm.utils import create_service_endpoint
        service_endpoints = [create_service_endpoint(service_endpoint)]
    
    # Создаем DID из ключа с service endpoints
    did_obj = create_peer_did_from_keypair(priv_key, service_endpoints=service_endpoints)
    did = did_obj.did
    did_document = did_obj.to_dict()
    
    return {
        "address": address,
        "key_type": key_type,
        "public_key": public_key_hex,
        "public_key_pem": public_key_pem,
        "did": did,
        "did_document": did_document,
        "service_endpoint": service_endpoint
    }


@app.get("/api/node/is-admin-configured", response_model=AdminConfiguredResponse)
async def check_admin_configured(db: DbDepends):
    """
    Check if admin has been configured with at least one auth method
    
    Returns:
        Admin configuration status
    """
    from sqlalchemy import select, func
    from db.models import AdminTronAddress
    from services.admin import AdminService
    
    is_configured = await AdminService.is_admin_configured(db)
    admin = await AdminService.get_admin(db)
    
    has_password = bool(admin and admin.username and admin.password_hash)
    
    result = await db.execute(
        select(func.count(AdminTronAddress.id))
        .where(AdminTronAddress.is_active == True)
    )
    tron_count = result.scalar()
    
    return AdminConfiguredResponse(
        configured=is_configured,
        has_password=has_password,
        tron_addresses_count=tron_count
    )


@app.post("/api/node/set-service-endpoint", response_model=ChangeResponse)
async def set_service_endpoint(
    request: SetServiceEndpointRequest,
    db: DbDepends,
    admin: AdminDepends = None
):
    """
    Set service endpoint for the node
    
    Args:
        request: Service endpoint configuration
        db: Database session
        
    Returns:
        Success status
        
    Note:
        If node is not initialized yet, this endpoint is accessible without authentication.
        Once node is initialized, authentication is required.
    """
    from services.admin import AdminService
    
    try:
        # Проверяем, инициализирована ли нода
        node_initialized = await NodeService.is_node_initialized(db)
        
        # Если нода уже инициализирована, требуем авторизацию
        if node_initialized and not admin:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Admin authentication required"
            )
        
        success = await NodeService.set_service_endpoint(
            db,
            request.service_endpoint
        )
        
        if not success:
            raise HTTPException(
                status_code=404,
                detail="Node not initialized"
            )
        
        return ChangeResponse(
            success=True,
            message="Service endpoint configured successfully"
        )
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error configuring service endpoint: {str(e)}"
        )


@app.get("/api/node/service-endpoint", response_model=ServiceEndpointResponse)
async def get_service_endpoint(
    db: DbDepends,
    admin: RequireAdminDepends
):
    """
    Get current service endpoint
    
    Args:
        db: Database session
        
    Returns:
        Service endpoint information
    """
    try:
        endpoint = await NodeService.get_service_endpoint(db)
        configured = await NodeService.is_service_endpoint_configured(db)
        
        return ServiceEndpointResponse(
            service_endpoint=endpoint,
            configured=configured
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error getting service endpoint: {str(e)}"
        )


@app.post("/api/node/test-service-endpoint", response_model=TestServiceEndpointResponse)
async def test_service_endpoint(request: TestServiceEndpointRequest):
    """
    Test service endpoint availability
    
    Args:
        request: Service endpoint to test
        
    Returns:
        Test result with status and response time
    """
    import httpx
    import time
    
    try:
        start_time = time.time()
        
        # Try to make a GET request to the endpoint
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                response = await client.get(request.service_endpoint)
                response_time_ms = (time.time() - start_time) * 1000
                
                # Check if we got a 200 OK
                if response.status_code == 200:
                    return TestServiceEndpointResponse(
                        success=True,
                        status_code=response.status_code,
                        message=f"Endpoint is accessible (HTTP {response.status_code})",
                        response_time_ms=round(response_time_ms, 2)
                    )
                else:
                    return TestServiceEndpointResponse(
                        success=False,
                        status_code=response.status_code,
                        message=f"Endpoint returned HTTP {response.status_code}, expected 200",
                        response_time_ms=round(response_time_ms, 2)
                    )
            except httpx.ConnectError:
                return TestServiceEndpointResponse(
                    success=False,
                    status_code=None,
                    message="Connection failed: Cannot connect to endpoint",
                    response_time_ms=None
                )
            except httpx.TimeoutException:
                return TestServiceEndpointResponse(
                    success=False,
                    status_code=None,
                    message="Request timeout: Endpoint took too long to respond",
                    response_time_ms=None
                )
            except Exception as e:
                return TestServiceEndpointResponse(
                    success=False,
                    status_code=None,
                    message=f"Request failed: {str(e)}",
                    response_time_ms=None
                )
                
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error testing endpoint: {str(e)}"
        )


@app.get("/api/node/is-service-endpoint-configured")
async def check_service_endpoint_configured(db: DbDepends):
    """
    Check if service endpoint has been configured
    
    Returns:
        Service endpoint configuration status
    """
    configured = await NodeService.is_service_endpoint_configured(db)
    
    return {"configured": configured}


# ====================
# Public Service Endpoint
# ====================

@app.get("/endpoint")
async def get_node_did_document(
    priv_key: PrivKeyDepends,
    db: DbDepends
):
    """
    Public endpoint that returns the node's DID Document
    
    This endpoint is the service endpoint advertised in the DID Document.
    It allows other nodes to discover the node's public keys and capabilities.
    Works even if node is not fully initialized (admin/service_endpoint not configured).
    
    Returns:
        DID Document in JSON format, or status message if node is not initialized
    """
    # If node key doesn't exist, return a simple status response with 200 OK
    if priv_key is None:
        has_key_in_db = await NodeService.has_key(db)
        
        # Return 200 OK with status message instead of 503
        return {
            "status": "not_initialized",
            "message": "Node is not initialized. Please initialize the node first.",
            "initialized": False
        }
    
    try:
        # Get service endpoint from database
        service_endpoint = await NodeService.get_service_endpoint(db)
        
        # Create service endpoints for DID if configured
        service_endpoints = None
        if service_endpoint:
            from didcomm.utils import create_service_endpoint
            service_endpoints = [create_service_endpoint(service_endpoint)]
        
        # Create DID with service endpoints
        did_obj = create_peer_did_from_keypair(priv_key, service_endpoints=service_endpoints)
        
        # Return DID Document
        return did_obj.to_dict()
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating DID Document: {str(e)}"
        )


@app.post("/endpoint")
async def receive_didcomm_message(
    message: dict,
    priv_key: PrivKeyDepends,
    db: DbDepends
):
    """
    Public endpoint that receives incoming DIDComm messages
    
    This endpoint is the service endpoint advertised in the DID Document.
    It accepts packed DIDComm messages, unpacks them, routes to appropriate
    protocol handlers, and returns any response.
    Works even if node is not fully initialized (admin/service_endpoint not configured).
    
    Args:
        message: Packed DIDComm message (can include sender_public_key and sender_key_type)
        priv_key: Node's private key (from dependencies)
        db: Database session
        
    Returns:
        Response message or success status
    """
    from didcomm.message import unpack_message
    from routers.utils import extract_protocol_name
    from services.protocols import get_protocol_handler
    
    # Check if node key exists
    if priv_key is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Node key not available"
        )
    
    try:
        # Extract optional sender info from message
        sender_public_key = None
        sender_key_type = None
        didcomm_message = message
        
        # Check if message includes metadata (sender_public_key, sender_key_type)
        if isinstance(message, dict):
            if "sender_public_key" in message:
                sender_public_key = bytes.fromhex(message["sender_public_key"])
                sender_key_type = message.get("sender_key_type")
                didcomm_message = message.get("message", message)
        
        # Unpack the message
        unpacked_message = unpack_message(
            didcomm_message,
            priv_key,
            sender_public_key=sender_public_key,
            sender_key_type=sender_key_type
        )
        
        # Extract protocol name from message type
        protocol_name = extract_protocol_name(unpacked_message.type)
        if not protocol_name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Could not determine protocol from message type: {unpacked_message.type}"
            )
        
        # Get protocol handler
        handler_class = get_protocol_handler(protocol_name)
        if not handler_class:
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail=f"Protocol '{protocol_name}' is not supported"
            )
        
        # Create handler instance
        did_obj = create_peer_did_from_keypair(priv_key)
        handler = handler_class(priv_key, did_obj.did)
        
        # Handle the message
        response_message = await handler.handle_message(
            unpacked_message,
            sender_public_key=sender_public_key,
            sender_key_type=sender_key_type
        )
        
        # If handler returns a response, pack it
        if response_message and sender_public_key:
            packed_response = handler.pack_response(
                response_message,
                [sender_public_key],
                encrypt=True
            )
            return {
                "success": True,
                "message": f"Message processed by {protocol_name} protocol",
                "response": packed_response
            }
        
        return {
            "success": True,
            "message": f"Message processed by {protocol_name} protocol"
        }
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid message format: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing message: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

