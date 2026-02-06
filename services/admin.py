"""
Service for managing admin user credentials
"""
from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from passlib.context import CryptContext
from db.models import AdminUser
import re

# Configure password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AdminService:
    """Service for managing admin credentials"""
    
    @staticmethod
    def hash_password(password: str) -> str:
        """
        Hash a password using bcrypt
        
        Args:
            password: Plain text password
            
        Returns:
            Hashed password
        """
        return pwd_context.hash(password)
    
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """
        Verify a password against its hash
        
        Args:
            plain_password: Plain text password to verify
            hashed_password: Hashed password to check against
            
        Returns:
            True if password matches, False otherwise
        """
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
    
    @staticmethod
    async def create_password_admin(
        username: str,
        password: str,
        db: AsyncSession
    ) -> AdminUser:
        """
        Create a new admin user with password authentication
        
        Args:
            username: Admin username
            password: Plain text password
            db: Database session
            
        Returns:
            Created AdminUser instance
            
        Raises:
            ValueError: If validation fails or admin already exists
        """
        # Validate inputs
        if not username or not password:
            raise ValueError("Username and password are required")
        
        if len(password) < 8:
            raise ValueError("Password must be at least 8 characters long")
        
        if len(username) < 3:
            raise ValueError("Username must be at least 3 characters long")
        
        # Check if admin already configured
        if await AdminService.is_admin_configured(db):
            raise ValueError("Admin already configured")
        
        # Check if username already exists
        result = await db.execute(
            select(AdminUser).where(AdminUser.username == username)
        )
        if result.scalar_one_or_none():
            raise ValueError(f"Username '{username}' already exists")
        
        # Hash password and create admin
        password_hash = AdminService.hash_password(password)
        
        admin_user = AdminUser(
            auth_method='password',
            username=username,
            password_hash=password_hash,
            tron_address=None,
            is_active=True
        )
        
        db.add(admin_user)
        await db.commit()
        await db.refresh(admin_user)
        
        return admin_user
    
    @staticmethod
    async def create_tron_admin(
        tron_address: str,
        db: AsyncSession
    ) -> AdminUser:
        """
        Create a new admin user with TRON authentication
        
        Args:
            tron_address: TRON wallet address
            db: Database session
            
        Returns:
            Created AdminUser instance
            
        Raises:
            ValueError: If validation fails or admin already exists
        """
        # Validate TRON address
        if not AdminService.validate_tron_address(tron_address):
            raise ValueError("Invalid TRON address format")
        
        # Check if admin already configured
        if await AdminService.is_admin_configured(db):
            raise ValueError("Admin already configured")
        
        # Check if TRON address already exists
        result = await db.execute(
            select(AdminUser).where(AdminUser.tron_address == tron_address)
        )
        if result.scalar_one_or_none():
            raise ValueError(f"TRON address '{tron_address}' already registered")
        
        # Create admin
        admin_user = AdminUser(
            auth_method='tron',
            username=None,
            password_hash=None,
            tron_address=tron_address,
            is_active=True
        )
        
        db.add(admin_user)
        await db.commit()
        await db.refresh(admin_user)
        
        return admin_user
    
    @staticmethod
    async def verify_password_admin(
        username: str,
        password: str,
        db: AsyncSession
    ) -> Optional[AdminUser]:
        """
        Verify admin credentials for password authentication
        
        Args:
            username: Admin username
            password: Plain text password
            db: Database session
            
        Returns:
            AdminUser if credentials are valid, None otherwise
        """
        # Find admin by username
        result = await db.execute(
            select(AdminUser).where(
                AdminUser.username == username,
                AdminUser.auth_method == 'password',
                AdminUser.is_active == True
            )
        )
        admin_user = result.scalar_one_or_none()
        
        if not admin_user or not admin_user.password_hash:
            return None
        
        # Verify password
        if AdminService.verify_password(password, admin_user.password_hash):
            return admin_user
        
        return None
    
    @staticmethod
    async def verify_tron_admin(
        tron_address: str,
        db: AsyncSession
    ) -> Optional[AdminUser]:
        """
        Check if TRON address is whitelisted as admin
        
        Args:
            tron_address: TRON wallet address
            db: Database session
            
        Returns:
            AdminUser if address is whitelisted, None otherwise
        """
        result = await db.execute(
            select(AdminUser).where(
                AdminUser.tron_address == tron_address,
                AdminUser.auth_method == 'tron',
                AdminUser.is_active == True
            )
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def is_admin_configured(db: AsyncSession) -> bool:
        """
        Check if any admin user exists
        
        Args:
            db: Database session
            
        Returns:
            True if at least one admin exists, False otherwise
        """
        result = await db.execute(
            select(AdminUser).where(AdminUser.is_active == True).limit(1)
        )
        return result.scalar_one_or_none() is not None
    
    @staticmethod
    async def init_from_env(admin_settings, db: AsyncSession) -> Optional[AdminUser]:
        """
        Initialize admin from environment variables if configured
        ENV VARS have priority over DB - will override existing admin
        
        Args:
            admin_settings: AdminSettings from Settings
            db: Database session
            
        Returns:
            Created/updated AdminUser or None if not configured
        """
        from sqlalchemy import delete
        
        # Check if admin settings are configured
        if not admin_settings.is_configured:
            return None
        
        # ENV VARS have priority: delete all existing admins
        if await AdminService.is_admin_configured(db):
            print("⚠ ENV VARS detected: overriding existing admin configuration")
            await db.execute(delete(AdminUser))
            await db.commit()
        
        # Create admin based on method
        try:
            if admin_settings.method == "password":
                if admin_settings.username and admin_settings.password:
                    admin = await AdminService.create_password_admin(
                        admin_settings.username,
                        admin_settings.password.get_secret_value(),
                        db
                    )
                    print(f"✓ Admin created from ENV: password (user: {admin_settings.username})")
                    return admin
            elif admin_settings.method == "tron":
                if admin_settings.tron_address:
                    admin = await AdminService.create_tron_admin(
                        admin_settings.tron_address,
                        db
                    )
                    print(f"✓ Admin created from ENV: tron (address: {admin_settings.tron_address})")
                    return admin
        except ValueError as e:
            # Validation error
            print(f"✗ Error: Could not create admin from ENV: {e}")
            return None
        
        return None

