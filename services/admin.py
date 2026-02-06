"""
Service for managing admin user credentials
New architecture: single admin with optional password + multiple TRON addresses
"""
from typing import Optional, Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, update, func
from passlib.context import CryptContext
from db.models import AdminUser, AdminTronAddress
import re

# Configure password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AdminService:
    """Service for managing admin credentials (single admin with multiple auth methods)"""
    
    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a password using bcrypt"""
        return pwd_context.hash(password)
    
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash"""
        return pwd_context.verify(plain_password, hashed_password)
    
    @staticmethod
    def validate_tron_address(address: str) -> bool:
        """
        Validate TRON address format
        
        Args:
            address: TRON address to validate
            
        Returns:
            True if valid TRON address, False otherwise
        """
        # TRON addresses start with 'T' and are 34 characters long (Base58)
        if not address or len(address) != 34:
            return False
        if not address.startswith('T'):
            return False
        # Base58 characters
        base58_pattern = r'^[123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz]+$'
        return bool(re.match(base58_pattern, address))
    
    # ====================
    # Admin User Management
    # ====================
    
    @staticmethod
    async def get_admin(db: AsyncSession) -> Optional[AdminUser]:
        """Get the single admin user (ID=1)"""
        result = await db.execute(
            select(AdminUser).where(AdminUser.id == 1)
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def ensure_admin_exists(db: AsyncSession) -> AdminUser:
        """Ensure admin user exists, create if not"""
        admin = await AdminService.get_admin(db)
        if not admin:
            admin = AdminUser(
                id=1,
                username=None,
                password_hash=None
            )
            db.add(admin)
            await db.commit()
            await db.refresh(admin)
        return admin
    
    @staticmethod
    async def is_admin_configured(db: AsyncSession) -> bool:
        """
        Check if admin has at least one authentication method configured
        
        Returns:
            True if admin has password OR at least one active TRON address
        """
        admin = await AdminService.get_admin(db)
        if not admin:
            return False
        
        # Check if password is configured
        has_password = bool(admin.username and admin.password_hash)
        
        # Check if at least one TRON address exists
        result = await db.execute(
            select(func.count(AdminTronAddress.id))
            .where(AdminTronAddress.is_active == True)
        )
        has_tron = result.scalar() > 0
        
        return has_password or has_tron
    
    # ====================
    # Password Management
    # ====================
    
    @staticmethod
    async def set_password(
        username: str,
        password: str,
        db: AsyncSession
    ) -> AdminUser:
        """
        Set or update admin password
        
        Args:
            username: Admin username
            password: Plain text password
            db: Database session
            
        Returns:
            Updated AdminUser
            
        Raises:
            ValueError: If validation fails
        """
        # Validate inputs
        if not username or not password:
            raise ValueError("Username and password are required")
        
        if len(password) < 8:
            raise ValueError("Password must be at least 8 characters long")
        
        if len(username) < 3:
            raise ValueError("Username must be at least 3 characters long")
        
        # Ensure admin exists
        admin = await AdminService.ensure_admin_exists(db)
        
        # Hash password and update
        password_hash = AdminService.hash_password(password)
        
        await db.execute(
            update(AdminUser)
            .where(AdminUser.id == 1)
            .values(username=username, password_hash=password_hash)
        )
        await db.commit()
        await db.refresh(admin)
        
        return admin
    
    @staticmethod
    async def change_password(
        old_password: str,
        new_password: str,
        db: AsyncSession
    ) -> AdminUser:
        """
        Change admin password (requires old password verification)
        
        Args:
            old_password: Current password
            new_password: New password
            db: Database session
            
        Returns:
            Updated AdminUser
            
        Raises:
            ValueError: If validation fails or old password is incorrect
        """
        admin = await AdminService.get_admin(db)
        if not admin or not admin.password_hash:
            raise ValueError("Password authentication not configured")
        
        # Verify old password
        if not AdminService.verify_password(old_password, admin.password_hash):
            raise ValueError("Incorrect current password")
        
        # Validate new password
        if len(new_password) < 8:
            raise ValueError("New password must be at least 8 characters long")
        
        # Update password
        password_hash = AdminService.hash_password(new_password)
        
        await db.execute(
            update(AdminUser)
            .where(AdminUser.id == 1)
            .values(password_hash=password_hash)
        )
        await db.commit()
        await db.refresh(admin)
        
        return admin
    
    @staticmethod
    async def remove_password(db: AsyncSession) -> AdminUser:
        """
        Remove password authentication (must have TRON addresses configured)
        
        Raises:
            ValueError: If no TRON addresses configured
        """
        # Check if at least one TRON address exists
        result = await db.execute(
            select(func.count(AdminTronAddress.id))
            .where(AdminTronAddress.is_active == True)
        )
        tron_count = result.scalar()
        
        if tron_count == 0:
            raise ValueError("Cannot remove password: no TRON addresses configured")
        
        admin = await AdminService.get_admin(db)
        if not admin:
            raise ValueError("Admin not found")
        
        # Remove password
        await db.execute(
            update(AdminUser)
            .where(AdminUser.id == 1)
            .values(username=None, password_hash=None)
        )
        await db.commit()
        await db.refresh(admin)
        
        return admin
    
    @staticmethod
    async def verify_password_auth(
        username: str,
        password: str,
        db: AsyncSession
    ) -> Optional[AdminUser]:
        """
        Verify admin credentials for password authentication
        
        Returns:
            AdminUser if credentials are valid, None otherwise
        """
        admin = await AdminService.get_admin(db)
        
        if not admin or not admin.username or not admin.password_hash:
            return None
        
        if admin.username != username:
            return None
        
        # Verify password
        if AdminService.verify_password(password, admin.password_hash):
            return admin
        
        return None
    
    # ====================
    # TRON Address Management
    # ====================
    
    @staticmethod
    async def add_tron_address(
        tron_address: str,
        db: AsyncSession,
        label: Optional[str] = None
    ) -> AdminTronAddress:
        """
        Add a TRON address to whitelist
        
        Args:
            tron_address: TRON wallet address
            label: Optional label for this address
            db: Database session
            
        Returns:
            Created AdminTronAddress
            
        Raises:
            ValueError: If validation fails or address already exists
        """
        # Validate TRON address
        if not AdminService.validate_tron_address(tron_address):
            raise ValueError("Invalid TRON address format")
        
        # Ensure admin exists
        await AdminService.ensure_admin_exists(db)
        
        # Check if address already exists
        result = await db.execute(
            select(AdminTronAddress).where(AdminTronAddress.tron_address == tron_address)
        )
        if result.scalar_one_or_none():
            raise ValueError(f"TRON address '{tron_address}' already registered")
        
        # Create TRON address
        tron_addr = AdminTronAddress(
            tron_address=tron_address,
            label=label,
            is_active=True
        )
        
        db.add(tron_addr)
        await db.commit()
        await db.refresh(tron_addr)
        
        return tron_addr
    
    @staticmethod
    async def get_tron_addresses(
        db: AsyncSession,
        active_only: bool = True
    ) -> List[AdminTronAddress]:
        """Get all TRON addresses"""
        query = select(AdminTronAddress)
        if active_only:
            query = query.where(AdminTronAddress.is_active == True)
        query = query.order_by(AdminTronAddress.created_at.desc())
        
        result = await db.execute(query)
        return list(result.scalars().all())
    
    @staticmethod
    async def update_tron_address(
        tron_id: int,
        db: AsyncSession,
        new_address: Optional[str] = None,
        new_label: Optional[str] = None
    ) -> AdminTronAddress:
        """
        Update TRON address or label
        
        Args:
            tron_id: ID of the address to update
            new_address: New TRON address (optional)
            new_label: New label (optional)
            db: Database session
            
        Returns:
            Updated AdminTronAddress
            
        Raises:
            ValueError: If validation fails or address not found
        """
        # Find address
        result = await db.execute(
            select(AdminTronAddress).where(AdminTronAddress.id == tron_id)
        )
        tron_addr = result.scalar_one_or_none()
        
        if not tron_addr:
            raise ValueError("TRON address not found")
        
        # Validate new address if provided
        if new_address:
            if not AdminService.validate_tron_address(new_address):
                raise ValueError("Invalid TRON address format")
            
            # Check if new address already exists (for different entry)
            result = await db.execute(
                select(AdminTronAddress).where(
                    AdminTronAddress.tron_address == new_address,
                    AdminTronAddress.id != tron_id
                )
            )
            if result.scalar_one_or_none():
                raise ValueError("TRON address already in use")
        
        # Update fields
        update_values = {}
        if new_address:
            update_values['tron_address'] = new_address
        if new_label is not None:  # Allow empty string to clear label
            update_values['label'] = new_label
        
        if update_values:
            await db.execute(
                update(AdminTronAddress)
                .where(AdminTronAddress.id == tron_id)
                .values(**update_values)
            )
            await db.commit()
            await db.refresh(tron_addr)
        
        return tron_addr
    
    @staticmethod
    async def toggle_tron_address(
        tron_id: int,
        is_active: bool,
        db: AsyncSession
    ) -> AdminTronAddress:
        """Toggle TRON address active status"""
        result = await db.execute(
            select(AdminTronAddress).where(AdminTronAddress.id == tron_id)
        )
        tron_addr = result.scalar_one_or_none()
        
        if not tron_addr:
            raise ValueError("TRON address not found")
        
        await db.execute(
            update(AdminTronAddress)
            .where(AdminTronAddress.id == tron_id)
            .values(is_active=is_active)
        )
        await db.commit()
        await db.refresh(tron_addr)
        
        return tron_addr
    
    @staticmethod
    async def delete_tron_address(
        tron_id: int,
        db: AsyncSession
    ) -> None:
        """
        Delete a TRON address
        
        Args:
            tron_id: ID of the address to delete
            db: Database session
            
        Raises:
            ValueError: If trying to delete the last authentication method
        """
        # Check if admin has password configured
        admin = await AdminService.get_admin(db)
        has_password = bool(admin and admin.username and admin.password_hash)
        
        # Count active TRON addresses
        result = await db.execute(
            select(func.count(AdminTronAddress.id))
            .where(AdminTronAddress.is_active == True)
        )
        tron_count = result.scalar()
        
        # Prevent deleting last auth method
        if not has_password and tron_count <= 1:
            raise ValueError("Cannot delete last authentication method. Add password or another TRON address first.")
        
        # Delete the address
        await db.execute(
            delete(AdminTronAddress).where(AdminTronAddress.id == tron_id)
        )
        await db.commit()
    
    @staticmethod
    async def verify_tron_auth(
        tron_address: str,
        db: AsyncSession
    ) -> bool:
        """
        Check if TRON address is whitelisted and active
        
        Returns:
            True if address is whitelisted and active
        """
        result = await db.execute(
            select(AdminTronAddress).where(
                AdminTronAddress.tron_address == tron_address,
                AdminTronAddress.is_active == True
            )
        )
        return result.scalar_one_or_none() is not None
    
    # ====================
    # Environment Variables Init
    # ====================
    
    @staticmethod
    async def init_from_env(admin_settings, db: AsyncSession) -> bool:
        """
        Initialize admin from environment variables if configured
        ENV VARS have priority over DB - will override existing config
        
        Args:
            admin_settings: AdminSettings from Settings
            db: Database session
            
        Returns:
            True if admin was initialized from env, False otherwise
        """
        # Check if admin settings are configured
        if not admin_settings.is_configured:
            return False
        
        print("⚠ ENV VARS detected: overriding existing admin configuration")
        
        # Clear existing data
        await db.execute(delete(AdminTronAddress))
        await db.execute(delete(AdminUser))
        await db.commit()
        
        # Ensure admin exists
        admin = await AdminService.ensure_admin_exists(db)
        
        # Configure based on method
        try:
            if admin_settings.method == "password":
                if admin_settings.username and admin_settings.password:
                    await AdminService.set_password(
                        admin_settings.username,
                        admin_settings.password.get_secret_value(),
                        db
                    )
                    print(f"✓ Admin password set from ENV (user: {admin_settings.username})")
                    return True
            elif admin_settings.method == "tron":
                if admin_settings.tron_address:
                    await AdminService.add_tron_address(
                        admin_settings.tron_address,
                        db,
                        label="From ENV"
                    )
                    print(f"✓ Admin TRON address added from ENV: {admin_settings.tron_address}")
                    return True
        except ValueError as e:
            print(f"✗ Error: Could not configure admin from ENV: {e}")
            return False
        
        return False
