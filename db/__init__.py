"""
Database models and configuration
"""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from settings import DatabaseSettings

# Base class for models
Base = declarative_base()

# Global session factory (will be initialized in init_db)
SessionLocal = None


def init_db(database_settings: DatabaseSettings):
    """Initialize database connection and session factory"""
    global SessionLocal
    
    engine = create_async_engine(
        database_settings.async_url,
        echo=database_settings.echo,
        pool_size=database_settings.pool_size,
        max_overflow=database_settings.max_overflow,
        pool_timeout=database_settings.pool_timeout,
    )
    
    SessionLocal = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False
    )
    
    return engine


async def get_db():
    """Dependency for getting database session"""
    if SessionLocal is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")
    
    async with SessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

