"""
Service for managing wallet user profiles (non-admin users)
"""
from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func, Numeric
from db.models import WalletUser, AdminTronAddress, AdminUser, Advertisement, Billing


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
    
    @staticmethod
    async def get_did_document(user_id: int, db: AsyncSession) -> Dict[str, Any]:
        """
        Get DID Document for a user with proofs, ratings, and other information
        
        Args:
            user_id: Wallet user ID
            db: Database session
            
        Returns:
            DID Document with user information, proofs, and ratings
            
        Raises:
            ValueError: If user not found
        """
        # Get user
        result = await db.execute(
            select(WalletUser).where(WalletUser.id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            raise ValueError(f"User with ID {user_id} not found")
        
        # Determine DID method and EC curve based on blockchain
        blockchain_lower = user.blockchain.lower()
        if blockchain_lower in ['tron', 'ethereum', 'bitcoin']:
            # TRON, Ethereum, Bitcoin use secp256k1
            did_method = "ethr" if blockchain_lower == "ethereum" else blockchain_lower
            did = f"did:{did_method}:{user.wallet_address.lower()}"
            ec_curve = "secp256k1"
            verification_method_type = "EcdsaSecp256k1VerificationKey2019"
            context_security = "https://w3id.org/security/suites/secp256k1-2019/v1"
        elif blockchain_lower in ['polkadot', 'substrate']:
            # Polkadot uses Ed25519
            did = f"did:polkadot:{user.wallet_address.lower()}"
            ec_curve = "Ed25519"
            verification_method_type = "Ed25519VerificationKey2018"
            context_security = "https://w3id.org/security/suites/ed25519-2018/v1"
        else:
            # Default to secp256k1 for unknown blockchains
            did = f"did:ethr:{user.wallet_address.lower()}"
            ec_curve = "secp256k1"
            verification_method_type = "EcdsaSecp256k1VerificationKey2019"
            context_security = "https://w3id.org/security/suites/secp256k1-2019/v1"
        
        # Get user statistics (from advertisements)
        ads_result = await db.execute(
            select(func.count(Advertisement.id), func.avg(func.cast(Advertisement.rating, Numeric)))
            .where(Advertisement.user_id == user_id)
        )
        stats = ads_result.first()
        ads_count = stats[0] or 0
        avg_rating = float(stats[1]) if stats[1] else 0.0
        
        # Get billing statistics
        billing_result = await db.execute(
            select(func.count(Billing.id), func.sum(Billing.usdt_amount))
            .where(Billing.wallet_user_id == user_id)
        )
        billing_stats = billing_result.first()
        transactions_count = billing_stats[0] or 0
        total_volume = float(billing_stats[1]) if billing_stats[1] else 0.0
        
        # Create DID Document with proofs and credentials
        did_document = {
            "@context": [
                "https://www.w3.org/ns/did/v1",
                context_security,
                "https://w3id.org/credentials/v1"
            ],
            "id": did,
            "controller": user.wallet_address,
            "verificationMethod": [
                {
                    "id": f"{did}#wallet",
                    "type": verification_method_type,
                    "controller": did,
                    "blockchainAccountId": f"{user.blockchain}:{user.wallet_address}",
                    "ecCurve": ec_curve
                }
            ],
            "authentication": [f"{did}#wallet"],
            "assertionMethod": [f"{did}#wallet"],
            "service": [
                {
                    "id": f"{did}#profile",
                    "type": "UserProfile",
                    "serviceEndpoint": f"/api/profile/user/{user_id}"
                }
            ],
            "proof": [
                {
                    "type": "VerificationProof",
                    "verificationStatus": user.is_verified,
                    "verifiedAt": user.updated_at.isoformat() if user.is_verified else None
                },
                {
                    "type": "RatingProof",
                    "averageRating": round(avg_rating, 1),
                    "totalDeals": ads_count,
                    "totalTransactions": transactions_count
                },
                {
                    "type": "BalanceProof",
                    "currentBalance": float(user.balance_usdt or 0),
                    "totalVolume": total_volume
                }
            ],
            "credential": {
                "nickname": user.nickname,
                "walletAddress": user.wallet_address,
                "blockchain": user.blockchain,
                "ecCurve": ec_curve,
                "isVerified": user.is_verified,
                "accessToAdminPanel": user.access_to_admin_panel,
                "createdAt": user.created_at.isoformat(),
                "updatedAt": user.updated_at.isoformat()
            }
        }
        
        return did_document

