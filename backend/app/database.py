import os
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession,
    async_sessionmaker,
)
from .config import settings
from backend.app.models.base import Base
from sqlalchemy.pool import NullPool


# Base engine kwargs
engine_kwargs = {"echo": settings.db_echo}

# Lambda freezes between calls, so pooled connections go stale. Disable pooling if on Lambda.
if os.environ.get("AWS_LAMBDA_FUNCTION_NAME"):
    engine_kwargs["poolclass"] = NullPool

# 2. Create the async engine
engine = create_async_engine(settings.database_url, **engine_kwargs)

# 3. Create a session Factory
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

