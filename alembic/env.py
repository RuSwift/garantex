"""
Alembic environment configuration
"""
from logging.config import fileConfig
from sqlalchemy import engine_from_config
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import AsyncEngine
from alembic import context
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add project root to path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

# Load environment variables from .env file in project root
env_file_path = project_root / ".env"
if env_file_path.exists():
    load_dotenv(env_file_path, override=False)

# Import settings and models
from settings import DatabaseSettings
from db import Base
from db.models import NodeSettings, Storage, AdminUser, AdminTronAddress, WalletUser, Connection, EscrowModel, Advertisement, Deals  # Import all models here

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Get database URL from settings
# Environment variables are now loaded from .env file, so DatabaseSettings will use them
db_settings = DatabaseSettings()

# Print connection parameters for debugging
print("=" * 60)
print("Database Connection Parameters:")
print(f"  Host: {db_settings.host}")
print(f"  Port: {db_settings.port}")
print(f"  User: {db_settings.user}")
print(f"  Database: {db_settings.database}")
print(f"  Password: {'***' if db_settings.password else '(not set)'}")
print(f"  .env file: {env_file_path} ({'found' if env_file_path.exists() else 'not found'})")
print("=" * 60)

config.set_main_option("sqlalchemy.url", db_settings.url)

# add your model's MetaData object here
# for 'autogenerate' support
target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    from sqlalchemy.ext.asyncio import create_async_engine
    
    # Create async engine from database settings
    connectable = create_async_engine(
        db_settings.async_url,
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    import asyncio
    asyncio.run(run_migrations_online())

