"""
Router for Marketplace API endpoints
"""
from fastapi import APIRouter, Depends
from dependencies import SettingsDepends, require_admin

router = APIRouter(
    prefix="/api/marketplace",
    tags=["marketplace"],
    dependencies=[Depends(require_admin)]
)


@router.get("/arbiter/is-initialized")
async def check_arbiter_initialized(
    settings: SettingsDepends
):
    """
    Check if arbiter wallet has been initialized
    
    Args:
        settings: Application settings
        
    Returns:
        Arbiter initialization status
    """
    is_initialized = bool(
        settings.marketplace.arbiter_mnemonic.phrase or 
        settings.marketplace.arbiter_mnemonic.encrypted_phrase
    )
    
    return {"initialized": is_initialized}

