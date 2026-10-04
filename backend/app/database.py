import os
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession,
    async_sessionmaker,
)
from backend.app.config import settings
from backend.app.models.base import Base

# 1. Define the connection URL
DATABASE_URL = settings.database_url

# 2. Create the async engine
engine = create_async_engine(DATABASE_URL, echo=True)

# 3. Create a session Factory
AsyncSessionLocal = async_sessionmaker(
    bind=engine, class_ =AsyncSession, expire_on_commit=False
)
