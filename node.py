from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from routers import auth
from routers import didcomm
from dependencies import UserDepends, SettingsDepends, PrivKeyDepends, DbDepends
from schemas.node import (
    NodeInitRequest, NodeInitPemRequest, NodeInitResponse,
    SetPasswordRequest, ChangePasswordRequest, AdminInfoResponse, AdminConfiguredResponse,
    TronAddressList, TronAddressItem, AddTronAddressRequest, UpdateTronAddressRequest,
    ToggleTronAddressRequest, ChangeResponse
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
                    "label": "Нода",
                    "sub": [],
                    "page": "Profile"
                },
                {
                    "id": "admin-account",
                    "href": "/admin-account",
                    "icon_class": "fas fa-user-shield",
                    "label": "Администрирование",
                    "sub": [],
                    "page": "AdminAccount"
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


@app.post("/api/admin/set-password", response_model=ChangeResponse)
async def set_admin_password(
    request: SetPasswordRequest,
    db: DbDepends
):
    """
    Set or update admin password
    
    Args:
        request: Password configuration
        db: Database session
        
    Returns:
        Success status
    """
    try:
        await AdminService.set_password(
            request.username,
            request.password,
            db
        )
        
        return ChangeResponse(
            success=True,
            message="Admin password configured successfully"
        )
            
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error configuring password: {str(e)}"
        )


@app.get("/api/node/is-admin-configured", response_model=AdminConfiguredResponse)
async def check_admin_configured(db: DbDepends):
    """
    Check if admin has been configured with at least one auth method
    
    Returns:
        Admin configuration status
    """
    from sqlalchemy import select, func
    from db.models import AdminTronAddress
    
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


@app.get("/api/admin/info", response_model=AdminInfoResponse)
async def get_admin_info(db: DbDepends):
    """
    Get information about the admin user
    
    Args:
        db: Database session
        
    Returns:
        Admin user information
    """
    from sqlalchemy import select, func
    from db.models import AdminUser, AdminTronAddress
    
    try:
        admin = await AdminService.get_admin(db)
        
        if not admin:
            raise HTTPException(
                status_code=404,
                detail="Admin not configured"
            )
        
        # Count TRON addresses
        result = await db.execute(
            select(func.count(AdminTronAddress.id))
            .where(AdminTronAddress.is_active == True)
        )
        tron_count = result.scalar()
        
        return AdminInfoResponse(
            id=admin.id,
            has_password=bool(admin.username and admin.password_hash),
            username=admin.username,
            tron_addresses_count=tron_count,
            created_at=admin.created_at,
            updated_at=admin.updated_at
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error loading admin info: {str(e)}"
        )


@app.post("/api/admin/change-password", response_model=ChangeResponse)
async def change_admin_password(
    request: ChangePasswordRequest,
    db: DbDepends
):
    """
    Change admin password
    
    Args:
        request: Change password request
        db: Database session
        
    Returns:
        Success status
    """
    try:
        await AdminService.change_password(
            request.old_password,
            request.new_password,
            db
        )
        
        return ChangeResponse(
            success=True,
            message="Password changed successfully"
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error changing password: {str(e)}"
        )


@app.delete("/api/admin/password", response_model=ChangeResponse)
async def remove_admin_password(db: DbDepends):
    """
    Remove admin password authentication (must have TRON addresses)
    
    Args:
        db: Database session
        
    Returns:
        Success status
    """
    try:
        await AdminService.remove_password(db)
        
        return ChangeResponse(
            success=True,
            message="Password removed successfully"
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error removing password: {str(e)}"
        )


@app.get("/api/admin/tron-addresses", response_model=TronAddressList)
async def get_tron_addresses(
    active_only: bool = True,
    db: DbDepends = None
):
    """
    Get list of all TRON admin addresses
    
    Args:
        active_only: Return only active addresses
        db: Database session
        
    Returns:
        List of TRON addresses
    """
    try:
        addresses = await AdminService.get_tron_addresses(db, active_only=active_only)
        
        items = [
            TronAddressItem(
                id=addr.id,
                tron_address=addr.tron_address,
                label=addr.label,
                is_active=addr.is_active,
                created_at=addr.created_at,
                updated_at=addr.updated_at
            )
            for addr in addresses
        ]
        
        return TronAddressList(addresses=items)
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error loading TRON addresses: {str(e)}"
        )


@app.post("/api/admin/tron-addresses", response_model=ChangeResponse)
async def add_tron_address(
    request: AddTronAddressRequest,
    db: DbDepends
):
    """
    Add new TRON address to whitelist
    
    Args:
        request: Add TRON address request
        db: Database session
        
    Returns:
        Success status
    """
    try:
        await AdminService.add_tron_address(
            request.tron_address,
            db,
            label=request.label
        )
        
        return ChangeResponse(
            success=True,
            message="TRON address added successfully"
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error adding TRON address: {str(e)}"
        )


@app.put("/api/admin/tron-addresses/{tron_id}", response_model=ChangeResponse)
async def update_tron_address(
    tron_id: int,
    request: UpdateTronAddressRequest,
    db: DbDepends
):
    """
    Update TRON address or label
    
    Args:
        tron_id: TRON address ID
        request: Update request
        db: Database session
        
    Returns:
        Success status
    """
    try:
        await AdminService.update_tron_address(
            tron_id,
            db,
            new_address=request.tron_address,
            new_label=request.label
        )
        
        return ChangeResponse(
            success=True,
            message="TRON address updated successfully"
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=400 if "not found" not in str(e).lower() else 404,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error updating TRON address: {str(e)}"
        )


@app.delete("/api/admin/tron-addresses/{tron_id}", response_model=ChangeResponse)
async def delete_tron_address(
    tron_id: int,
    db: DbDepends
):
    """
    Delete TRON address from whitelist
    
    Args:
        tron_id: TRON address ID
        db: Database session
        
    Returns:
        Success status
    """
    try:
        await AdminService.delete_tron_address(tron_id, db)
        
        return ChangeResponse(
            success=True,
            message="TRON address deleted successfully"
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error deleting TRON address: {str(e)}"
        )


@app.patch("/api/admin/tron-addresses/{tron_id}/toggle", response_model=ChangeResponse)
async def toggle_tron_address(
    tron_id: int,
    request: ToggleTronAddressRequest,
    db: DbDepends
):
    """
    Toggle TRON address active status
    
    Args:
        tron_id: TRON address ID
        request: Toggle request
        db: Database session
        
    Returns:
        Success status
    """
    try:
        await AdminService.toggle_tron_address(tron_id, request.is_active, db)
        
        status = "activated" if request.is_active else "deactivated"
        return ChangeResponse(
            success=True,
            message=f"TRON address {status} successfully"
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=400 if "not found" not in str(e).lower() else 404,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error toggling TRON address: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

