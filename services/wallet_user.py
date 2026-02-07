"""
Service for managing wallet user profiles (non-admin users)
"""
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from db.models import WalletUser, AdminTronAddress, AdminUser


class WalletUserService:
    """Service for managing wallet user profiles"""
    
    @staticmethod
    async def get_by_wallet_address(
        wallet_address: str,
        db: AsyncSession
    ) -> Optional[WalletUser]:
        """
        Get wallet user by wallet address
        
        Args:
            wallet_address: Wallet address to search for
            db: Database session
            
        Returns:
            WalletUser if found, None otherwise
        """
        result = await db.execute(
            select(WalletUser).where(WalletUser.wallet_address == wallet_address)
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def create_user(
        wallet_address: str,
        blockchain: str,
        nickname: str,
        db: AsyncSession
    ) -> WalletUser:
        """
        Create a new wallet user
        
        Args:
            wallet_address: User's wallet address
            blockchain: Blockchain type (tron, ethereum, etc.)
            nickname: User's display name
            db: Database session
            
        Returns:
            Created WalletUser
            
        Raises:
            ValueError: If user already exists or validation fails
        """
        # Check if user already exists
        existing = await WalletUserService.get_by_wallet_address(wallet_address, db)
        if existing:
            raise ValueError(f"User with wallet address '{wallet_address}' already exists")
        
        # Validate nickname
        if not nickname or len(nickname.strip()) == 0:
            raise ValueError("Nickname cannot be empty")
        
        if len(nickname) > 100:
            raise ValueError("Nickname cannot exceed 100 characters")
        
        # Validate blockchain
        if not blockchain or blockchain not in ['tron', 'ethereum', 'bitcoin']:
            raise ValueError("Invalid blockchain type")
        
        # Create user
        user = WalletUser(
            wallet_address=wallet_address,
            blockchain=blockchain,
            nickname=nickname.strip()
        )
        
        db.add(user)
        await db.commit()
        await db.refresh(user)
        
        return user
    
    @staticmethod
    async def get_by_nickname(
        nickname: str,
        db: AsyncSession
    ) -> Optional[WalletUser]:
        """
        Get wallet user by nickname
        
        Args:
            nickname: Nickname to search for
            db: Database session
            
        Returns:
            WalletUser if found, None otherwise
        """
        result = await db.execute(
            select(WalletUser).where(WalletUser.nickname == nickname)
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def update_nickname(
        wallet_address: str,
        new_nickname: str,
        db: AsyncSession
    ) -> WalletUser:
        """
        Update user's nickname
        
        Args:
            wallet_address: User's wallet address
            new_nickname: New nickname
            db: Database session
            
        Returns:
            Updated WalletUser
            
        Raises:
            ValueError: If user not found or validation fails
        """
        user = await WalletUserService.get_by_wallet_address(wallet_address, db)
        if not user:
            raise ValueError("User not found")
        
        # Validate nickname
        if not new_nickname or len(new_nickname.strip()) == 0:
            raise ValueError("Nickname cannot be empty")
        
        if len(new_nickname) > 100:
            raise ValueError("Nickname cannot exceed 100 characters")
        
        # Check if nickname is already taken by another user
        existing_user = await WalletUserService.get_by_nickname(new_nickname.strip(), db)
        if existing_user and existing_user.wallet_address != wallet_address:
            raise ValueError(f"Nickname '{new_nickname}' is already taken by another user")
        
        # Update nickname
        await db.execute(
            update(WalletUser)
            .where(WalletUser.wallet_address == wallet_address)
            .values(nickname=new_nickname.strip())
        )
        await db.commit()
        await db.refresh(user)
        
        return user
    
    @staticmethod
    async def update_profile(
        wallet_address: str,
        nickname: Optional[str] = None,
        avatar: Optional[str] = None,
        db: AsyncSession = None
    ) -> WalletUser:
        """
        Update user's profile (nickname and/or avatar)
        
        Args:
            wallet_address: User's wallet address
            nickname: New nickname (optional, pass empty string to skip)
            avatar: New avatar in base64 format (optional, pass empty string to clear)
            db: Database session
            
        Returns:
            Updated WalletUser
            
        Raises:
            ValueError: If user not found or validation fails
        """
        user = await WalletUserService.get_by_wallet_address(wallet_address, db)
        if not user:
            raise ValueError("User not found")
        
        update_values = {}
        
        # Update nickname if provided and not empty
        if nickname is not None and nickname.strip():
            nickname = nickname.strip()
            
            # Validate nickname length
            if len(nickname) > 100:
                raise ValueError("Nickname cannot exceed 100 characters")
            
            # Check if nickname is already taken by another user
            existing_user = await WalletUserService.get_by_nickname(nickname, db)
            if existing_user and existing_user.wallet_address != wallet_address:
                raise ValueError(f"Nickname '{nickname}' is already taken")
            
            update_values['nickname'] = nickname
        
        # Update avatar if provided (empty string clears avatar)
        if avatar is not None:
            # Allow empty string to clear avatar
            if avatar == "":
                update_values['avatar'] = None
            else:
                # Validate avatar format (should be data:image/...)
                if not avatar.startswith('data:image/'):
                    raise ValueError("Avatar must be in base64 format starting with 'data:image/'")
                
                # Limit avatar size (e.g., 1MB base64)
                if len(avatar) > 1_500_000:  # ~1MB base64
                    raise ValueError("Avatar size is too large (max 1MB)")
                
                update_values['avatar'] = avatar
        
        # Check that at least one field is being updated
        if not update_values:
            raise ValueError("At least one field (nickname or avatar) must be provided")
        
        # Apply updates
        await db.execute(
            update(WalletUser)
            .where(WalletUser.wallet_address == wallet_address)
            .values(**update_values)
        )
        await db.commit()
        await db.refresh(user)
        
        return user
    
    @staticmethod
    async def is_admin_tron_wallet(
        tron_address: str,
        db: AsyncSession
    ) -> bool:
        """
        Check if TRON wallet address is in admin whitelist
        
        Args:
            tron_address: TRON wallet address to check
            db: Database session
            
        Returns:
            True if address is in admin whitelist, False otherwise
        """
        result = await db.execute(
            select(AdminTronAddress).where(
                AdminTronAddress.tron_address == tron_address,
                AdminTronAddress.is_active == True
            )
        )
        return result.scalar_one_or_none() is not None
    
    @staticmethod
    async def is_admin_password_configured(db: AsyncSession) -> bool:
        """
        Check if admin password authentication is configured
        
        Args:
            db: Database session
            
        Returns:
            True if admin has password configured
        """
        result = await db.execute(
            select(AdminUser).where(AdminUser.id == 1)
        )
        admin = result.scalar_one_or_none()
        
        if not admin:
            return False
        
        return bool(admin.username and admin.password_hash)

