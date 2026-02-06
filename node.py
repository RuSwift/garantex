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
    RootCredentialsRequest, RootCredentialsResponse,
    AdminInfoResponse, ChangePasswordRequest, ChangeTronAddressRequest, ChangeResponse,
    TronAddressList, TronAddressItem, AddTronAddressRequest, UpdateTronAddressRequest
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
    if settings.is_admin_configured_from_env:
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


@app.post("/api/node/set-root-credentials", response_model=RootCredentialsResponse)
async def set_root_credentials(
    request: RootCredentialsRequest,
    db: DbDepends
):
    """
    Set root admin credentials during node initialization (Step 2)
    
    Args:
        request: Root credentials configuration
        db: Database session
        
    Returns:
        Success status and configured auth method
    """
    try:
        if request.method == "password":
            if not request.username or not request.password:
                raise HTTPException(
                    status_code=400,
                    detail="Username and password required for password method"
                )
            
            # Create password admin
            admin_user = await AdminService.create_password_admin(
                request.username,
                request.password,
                db
            )
            
            return RootCredentialsResponse(
                success=True,
                message="Admin credentials configured successfully",
                auth_method="password"
            )
            
        elif request.method == "tron":
            if not request.tron_address:
                raise HTTPException(
                    status_code=400,
                    detail="TRON address required for tron method"
                )
            
            # Create TRON admin
            admin_user = await AdminService.create_tron_admin(
                request.tron_address,
                db
            )
            
            return RootCredentialsResponse(
                success=True,
                message="TRON admin configured successfully",
                auth_method="tron"
            )
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid method: {request.method}. Must be 'password' or 'tron'"
            )
            
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error configuring admin: {str(e)}"
        )


@app.get("/api/node/is-admin-configured")
async def check_admin_configured(db: DbDepends):
    """
    Check if admin user has been configured
    
    Returns:
        Boolean indicating if admin is configured
    """
    is_configured = await AdminService.is_admin_configured(db)
    return {"configured": is_configured}


@app.get("/api/admin/info", response_model=AdminInfoResponse)
async def get_admin_info(db: DbDepends):
    """
    Get information about the current admin user
    
    Args:
        db: Database session
        
    Returns:
        Admin user information
    """
    from sqlalchemy import select
    from db.models import AdminUser
    
    try:
        # Get the first active admin user
        result = await db.execute(
            select(AdminUser).where(AdminUser.is_active == True).limit(1)
        )
        admin_user = result.scalar_one_or_none()
        
        if not admin_user:
            raise HTTPException(
                status_code=404,
                detail="Admin user not found"
            )
        
        return AdminInfoResponse(
            id=admin_user.id,
            auth_method=admin_user.auth_method,
            username=admin_user.username,
            tron_address=admin_user.tron_address,
            is_active=admin_user.is_active,
            created_at=admin_user.created_at,
            updated_at=admin_user.updated_at
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
    Change admin password (for password authentication)
    
    Args:
        request: Change password request
        db: Database session
        
    Returns:
        Success status
    """
    from sqlalchemy import select, update
    from db.models import AdminUser
    
    try:
        # Get the first active admin user with password auth
        result = await db.execute(
            select(AdminUser).where(
                AdminUser.is_active == True,
                AdminUser.auth_method == 'password'
            ).limit(1)
        )
        admin_user = result.scalar_one_or_none()
        
        if not admin_user:
            raise HTTPException(
                status_code=404,
                detail="Admin user not found or not using password authentication"
            )
        
        # Verify old password
        if not admin_user.password_hash:
            raise HTTPException(
                status_code=400,
                detail="Password not set"
            )
        
        if not AdminService.verify_password(request.old_password, admin_user.password_hash):
            raise HTTPException(
                status_code=401,
                detail="Incorrect old password"
            )
        
        # Validate new password
        if len(request.new_password) < 8:
            raise HTTPException(
                status_code=400,
                detail="New password must be at least 8 characters long"
            )
        
        # Hash new password
        new_password_hash = AdminService.hash_password(request.new_password)
        
        # Update password
        await db.execute(
            update(AdminUser)
            .where(AdminUser.id == admin_user.id)
            .values(password_hash=new_password_hash)
        )
        await db.commit()
        
        return ChangeResponse(
            success=True,
            message="Password changed successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error changing password: {str(e)}"
        )


@app.post("/api/admin/change-tron-address", response_model=ChangeResponse)
async def change_admin_tron_address(
    request: ChangeTronAddressRequest,
    db: DbDepends
):
    """
    Change admin TRON address (for TRON authentication)
    
    Args:
        request: Change TRON address request
        db: Database session
        
    Returns:
        Success status
    """
    from sqlalchemy import select, update
    from db.models import AdminUser
    
    try:
        # Get the first active admin user with TRON auth
        result = await db.execute(
            select(AdminUser).where(
                AdminUser.is_active == True,
                AdminUser.auth_method == 'tron'
            ).limit(1)
        )
        admin_user = result.scalar_one_or_none()
        
        if not admin_user:
            raise HTTPException(
                status_code=404,
                detail="Admin user not found or not using TRON authentication"
            )
        
        # Validate TRON address
        if not AdminService.validate_tron_address(request.new_tron_address):
            raise HTTPException(
                status_code=400,
                detail="Invalid TRON address format"
            )
        
        # Check if address already exists
        result = await db.execute(
            select(AdminUser).where(
                AdminUser.tron_address == request.new_tron_address,
                AdminUser.id != admin_user.id
            )
        )
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=400,
                detail="TRON address already in use"
            )
        
        # Update TRON address
        await db.execute(
            update(AdminUser)
            .where(AdminUser.id == admin_user.id)
            .values(tron_address=request.new_tron_address)
        )
        await db.commit()
        
        return ChangeResponse(
            success=True,
            message="TRON address changed successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error changing TRON address: {str(e)}"
        )


@app.get("/api/admin/tron-addresses", response_model=TronAddressList)
async def get_tron_addresses(db: DbDepends):
    """
    Get list of all TRON admin addresses
    
    Args:
        db: Database session
        
    Returns:
        List of TRON addresses
    """
    from sqlalchemy import select
    from db.models import AdminUser
    
    try:
        result = await db.execute(
            select(AdminUser).where(
                AdminUser.auth_method == 'tron',
                AdminUser.is_active == True
            ).order_by(AdminUser.created_at.desc())
        )
        admins = result.scalars().all()
        
        addresses = [
            TronAddressItem(
                id=admin.id,
                tron_address=admin.tron_address,
                created_at=admin.created_at,
                is_active=admin.is_active
            )
            for admin in admins
        ]
        
        return TronAddressList(addresses=addresses)
        
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
    Add new TRON admin address
    
    Args:
        request: Add TRON address request
        db: Database session
        
    Returns:
        Success status
    """
    try:
        # Create new TRON admin (allow multiple)
        admin_user = await AdminService.create_tron_admin(
            request.tron_address,
            db,
            allow_multiple=True
        )
        
        return ChangeResponse(
            success=True,
            message=f"TRON address added successfully"
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


@app.put("/api/admin/tron-addresses/{admin_id}", response_model=ChangeResponse)
async def update_tron_address(
    admin_id: int,
    request: UpdateTronAddressRequest,
    db: DbDepends
):
    """
    Update TRON admin address
    
    Args:
        admin_id: Admin ID
        request: Update TRON address request
        db: Database session
        
    Returns:
        Success status
    """
    from sqlalchemy import select, update
    from db.models import AdminUser
    
    try:
        # Find admin by ID
        result = await db.execute(
            select(AdminUser).where(
                AdminUser.id == admin_id,
                AdminUser.auth_method == 'tron',
                AdminUser.is_active == True
            )
        )
        admin_user = result.scalar_one_or_none()
        
        if not admin_user:
            raise HTTPException(
                status_code=404,
                detail="TRON admin not found"
            )
        
        # Validate new TRON address
        if not AdminService.validate_tron_address(request.new_tron_address):
            raise HTTPException(
                status_code=400,
                detail="Invalid TRON address format"
            )
        
        # Check if new address already exists (for different admin)
        result = await db.execute(
            select(AdminUser).where(
                AdminUser.tron_address == request.new_tron_address,
                AdminUser.id != admin_id
            )
        )
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=400,
                detail="TRON address already in use"
            )
        
        # Update TRON address
        await db.execute(
            update(AdminUser)
            .where(AdminUser.id == admin_id)
            .values(tron_address=request.new_tron_address)
        )
        await db.commit()
        
        return ChangeResponse(
            success=True,
            message="TRON address updated successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error updating TRON address: {str(e)}"
        )


@app.delete("/api/admin/tron-addresses/{admin_id}", response_model=ChangeResponse)
async def delete_tron_address(
    admin_id: int,
    db: DbDepends
):
    """
    Delete TRON admin address
    
    Args:
        admin_id: Admin ID
        db: Database session
        
    Returns:
        Success status
    """
    from sqlalchemy import select, delete, func
    from db.models import AdminUser
    
    try:
        # Find admin by ID first
        result = await db.execute(
            select(AdminUser).where(
                AdminUser.id == admin_id,
                AdminUser.auth_method == 'tron',
                AdminUser.is_active == True
            )
        )
        admin_user = result.scalar_one_or_none()
        
        if not admin_user:
            raise HTTPException(
                status_code=404,
                detail="TRON admin not found"
            )
        
        # Check if this is the last admin
        result = await db.execute(
            select(func.count(AdminUser.id)).where(AdminUser.is_active == True)
        )
        total_admins = result.scalar()
        
        if total_admins <= 1:
            raise HTTPException(
                status_code=400,
                detail="Cannot delete the last admin. At least one admin must exist."
            )
        
        # Delete admin
        await db.execute(
            delete(AdminUser).where(AdminUser.id == admin_id)
        )
        await db.commit()
        
        return ChangeResponse(
            success=True,
            message="TRON address deleted successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error deleting TRON address: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

