"""
Base repository class for working with storage table
"""
from typing import Optional, List, Type, Dict, Any
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete as sql_delete
from pydantic import BaseModel
from db.models import Storage


class BaseRepo:
    """
    Base repository class for working with storage table
    
    Automatically filters records by space and supports versioned Pydantic schemas.
    Subclasses can override schema_v1, schema_v2, etc. to define their own schemas.
    
    Usage:
        class UserRepo(BaseRepo):
            schema_v1 = UserSchemaV1
            schema_v2 = UserSchemaV2
        
        repo = UserRepo(session, space="users")
        user = await repo.create({"name": "John"}, schema_ver="1")
    """
    
    # Versioned schemas - subclasses can override these
    schema_v1: Optional[Type[BaseModel]] = None
    schema_v2: Optional[Type[BaseModel]] = None
    schema_v3: Optional[Type[BaseModel]] = None
    schema_v4: Optional[Type[BaseModel]] = None
    schema_v5: Optional[Type[BaseModel]] = None
    
    def __init__(self, session: AsyncSession, space: str):
        """
        Initialize repository
        
        Args:
            session: SQLAlchemy async session
            space: Space identifier for filtering records
        """
        self.session = session
        self.space = space
    
    async def create(self, payload: Dict[str, Any], schema_ver: str = "1") -> Storage:
        """
        Create a new storage record
        
        Args:
            payload: JSON payload data
            schema_ver: Schema version (default: "1")
            
        Returns:
            Created Storage record
        """
        storage = Storage(
            space=self.space,
            payload=payload,
            schema_ver=schema_ver
        )
        self.session.add(storage)
        await self.session.flush()
        await self.session.refresh(storage)
        return storage
    
    async def get_by_uuid(self, uuid: UUID) -> Optional[Storage]:
        """
        Get storage record by UUID
        
        Args:
            uuid: Record UUID
            
        Returns:
            Storage record or None if not found
        """
        stmt = select(Storage).where(
            Storage.uuid == uuid,
            Storage.space == self.space
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_all(self) -> List[Storage]:
        """
        Get all storage records in the current space
        
        Returns:
            List of Storage records
        """
        stmt = select(Storage).where(
            Storage.space == self.space
        ).order_by(Storage.created_at.desc())
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
    
    async def get_by_schema_ver(self, schema_ver: str) -> List[Storage]:
        """
        Get all storage records with specific schema version
        
        Args:
            schema_ver: Schema version to filter by
            
        Returns:
            List of Storage records
        """
        stmt = select(Storage).where(
            Storage.space == self.space,
            Storage.schema_ver == schema_ver
        ).order_by(Storage.created_at.desc())
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
    
    async def update(
        self, 
        uuid: UUID, 
        payload: Dict[str, Any], 
        schema_ver: Optional[str] = None
    ) -> Optional[Storage]:
        """
        Update storage record
        
        Args:
            uuid: Record UUID
            payload: New JSON payload data
            schema_ver: New schema version (optional, keeps existing if None)
            
        Returns:
            Updated Storage record or None if not found
        """
        storage = await self.get_by_uuid(uuid)
        if storage is None:
            return None
        
        storage.payload = payload
        if schema_ver is not None:
            storage.schema_ver = schema_ver
        
        await self.session.flush()
        await self.session.refresh(storage)
        return storage
    
    async def delete(self, uuid: UUID) -> bool:
        """
        Delete storage record
        
        Args:
            uuid: Record UUID
            
        Returns:
            True if record was deleted, False if not found
        """
        stmt = sql_delete(Storage).where(
            Storage.uuid == uuid,
            Storage.space == self.space
        )
        result = await self.session.execute(stmt)
        return result.rowcount > 0
    
    def get_schema(self, version: str) -> Optional[Type[BaseModel]]:
        """
        Get Pydantic schema by version
        
        Args:
            version: Schema version ("1", "2", etc.)
            
        Returns:
            Pydantic schema class or None if not defined
        """
        schema_attr = f"schema_v{version}"
        return getattr(self, schema_attr, None)
    
    def validate_payload(self, payload: Dict[str, Any], version: str) -> BaseModel:
        """
        Validate payload against versioned schema
        
        Args:
            payload: Data to validate
            version: Schema version to use
            
        Returns:
            Validated Pydantic model instance
            
        Raises:
            ValueError: If schema for version is not defined
            ValidationError: If payload doesn't match schema
        """
        schema = self.get_schema(version)
        if schema is None:
            raise ValueError(f"Schema version {version} is not defined for {self.__class__.__name__}")
        
        return schema(**payload)

