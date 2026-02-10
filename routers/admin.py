"""
Router for Admin API endpoints
"""
from fastapi import APIRouter, HTTPException, status
from dependencies import AdminDepends, RequireAdminDepends, SettingsDepends, DbDepends
from schemas.node import (
    AdminLoginRequest, AdminLoginResponse,
    AdminTronNonceRequest, AdminTronNonceResponse, AdminTronVerifyRequest,
    SetPasswordRequest, ChangePasswordRequest, AdminInfoResponse,
    ChangeResponse,
    TronAddressList, TronAddressItem, AddTronAddressRequest, UpdateTronAddressRequest,
    ToggleTronAddressRequest
)
from services.admin import AdminService
from services.node import NodeService
from services.tron_auth import tron_auth
import jwt
from datetime import datetime, timedelta
from sqlalchemy import select, func
from db.models import AdminTronAddress

router = APIRouter(
    prefix="/api/admin",
    tags=["admin"]
)


@router.post("/login", response_model=AdminLoginResponse)
async def admin_login(
    request: AdminLoginRequest,
    db: DbDepends,
    settings: SettingsDepends
):
    """
    Admin login with username and password
    
    Args:
        request: Login credentials
        db: Database session
        settings: Application settings
        
    Returns:
        JWT token for authenticated admin
    """
    try:
        # Verify credentials
        admin = await AdminService.verify_password_auth(
            request.username,
            request.password,
            db
        )
        
        if not admin:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password"
            )
        
        # Generate JWT token
        payload = {
            "admin": True,
            "username": admin.username,
            "exp": datetime.utcnow() + timedelta(hours=24),
            "iat": datetime.utcnow()
        }
        
        token = jwt.encode(
            payload,
            settings.secret.get_secret_value(),
            algorithm="HS256"
        )
        
        return AdminLoginResponse(
            success=True,
            token=token,
            message="Login successful"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Login error: {str(e)}"
        )


@router.post("/tron/nonce", response_model=AdminTronNonceResponse)
async def admin_tron_nonce(
    request: AdminTronNonceRequest,
    db: DbDepends
):
    """
    Get nonce for TRON wallet authentication
    
    Args:
        request: TRON address
        db: Database session
        
    Returns:
        Nonce and message to sign
    """
    try:
        # Check if TRON address is whitelisted
        is_whitelisted = await AdminService.verify_tron_auth(
            request.tron_address,
            db
        )
        
        if not is_whitelisted:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="TRON address not authorized for admin access"
            )
        
        # Generate nonce
        nonce = tron_auth.generate_nonce(request.tron_address)
        message = f"Please sign this message to authenticate:\n\nNonce: {nonce}"
        
        return AdminTronNonceResponse(
            nonce=nonce,
            message=message
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating nonce: {str(e)}"
        )


@router.post("/tron/verify", response_model=AdminLoginResponse)
async def admin_tron_verify(
    request: AdminTronVerifyRequest,
    db: DbDepends,
    settings: SettingsDepends
):
    """
    Verify TRON signature and authenticate admin
    
    Args:
        request: TRON address, signature, and message
        db: Database session
        settings: Application settings
        
    Returns:
        JWT token for authenticated admin
    """
    try:
        # Check if TRON address is whitelisted
        is_whitelisted = await AdminService.verify_tron_auth(
            request.tron_address,
            db
        )
        
        if not is_whitelisted:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="TRON address not authorized for admin access"
            )
        
        # Verify signature
        is_valid = tron_auth.verify_signature(
            request.tron_address,
            request.signature,
            request.message
        )
        
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid signature"
            )
        
        # Generate JWT token
        payload = {
            "admin": True,
            "tron_address": request.tron_address,
            "blockchain": "tron",
            "exp": datetime.utcnow() + timedelta(hours=24),
            "iat": datetime.utcnow()
        }
        
        token = jwt.encode(
            payload,
            settings.secret.get_secret_value(),
            algorithm="HS256"
        )
        
        return AdminLoginResponse(
            success=True,
            token=token,
            message="Authentication successful"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Verification error: {str(e)}"
        )


@router.post("/logout")
async def admin_logout():
    """
    Admin logout endpoint
    
    Note: JWT tokens are stateless, so logout is handled client-side by removing the token.
    This endpoint exists for consistency and future stateful token management.
    """
    return {
        "success": True,
        "message": "Logged out successfully"
    }


@router.post("/set-password", response_model=ChangeResponse)
async def set_admin_password(
    request: SetPasswordRequest,
    db: DbDepends,
    settings: SettingsDepends,
    admin_cookie: AdminDepends
):
    """
    Set or update admin password
    
    Если нода еще не инициализирована - endpoint публичный (для первичной настройки)
    Если нода уже инициализирована - требуется авторизация
    
    Args:
        request: Password configuration
        db: Database session
        settings: Application settings
        admin_cookie: Admin info from cookie (optional)
        
    Returns:
        Success status
    """
    # Проверяем, инициализирована ли нода
    node_initialized = await NodeService.is_node_initialized(db)
    
    # Если нода уже инициализирована, требуем авторизацию
    if node_initialized and not admin_cookie:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Admin authentication required"
        )
    
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


@router.get("/info", response_model=AdminInfoResponse)
async def get_admin_info(
    db: DbDepends,
    admin: RequireAdminDepends
):
    """
    Get information about the admin user
    
    Args:
        db: Database session
        
    Returns:
        Admin user information
    """
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


@router.post("/change-password", response_model=ChangeResponse)
async def change_admin_password(
    request: ChangePasswordRequest,
    db: DbDepends,
    admin: RequireAdminDepends
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


@router.delete("/password", response_model=ChangeResponse)
async def remove_admin_password(
    db: DbDepends,
    admin: RequireAdminDepends
):
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


@router.get("/tron-addresses", response_model=TronAddressList)
async def get_tron_addresses(
    active_only: bool = True,
    db: DbDepends = None,
    admin: RequireAdminDepends = None
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


@router.post("/tron-addresses", response_model=ChangeResponse)
async def add_tron_address(
    request: AddTronAddressRequest,
    db: DbDepends,
    admin: AdminDepends = None
):
    """
    Add new TRON address to whitelist
    
    Если нода еще не инициализирована - endpoint публичный (для первичной настройки)
    Если нода уже инициализирована - требуется авторизация
    
    Args:
        request: Add TRON address request
        db: Database session
        
    Returns:
        Success status
    """
    try:
        # Проверяем, инициализирована ли нода
        node_initialized = await NodeService.is_node_initialized(db)
        
        # Если нода уже инициализирована, требуем авторизацию
        if node_initialized and not admin:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Admin authentication required"
            )
        
        await AdminService.add_tron_address(
            request.tron_address,
            db,
            label=request.label
        )
        
        return ChangeResponse(
            success=True,
            message="TRON address added successfully"
        )
        
    except HTTPException:
        raise
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


@router.put("/tron-addresses/{tron_id}", response_model=ChangeResponse)
async def update_tron_address(
    tron_id: int,
    request: UpdateTronAddressRequest,
    db: DbDepends,
    admin: RequireAdminDepends
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


@router.delete("/tron-addresses/{tron_id}", response_model=ChangeResponse)
async def delete_tron_address(
    tron_id: int,
    db: DbDepends,
    admin: RequireAdminDepends
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


@router.patch("/tron-addresses/{tron_id}/toggle", response_model=ChangeResponse)
async def toggle_tron_address(
    tron_id: int,
    request: ToggleTronAddressRequest,
    db: DbDepends,
    admin: RequireAdminDepends
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
        await AdminService.toggle_tron_address(
            tron_id,
            request.is_active,
            db
        )
        
        return ChangeResponse(
            success=True,
            message=f"TRON address {'activated' if request.is_active else 'deactivated'} successfully"
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

