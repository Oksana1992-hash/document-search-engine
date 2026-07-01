import os
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession,
    async_sessionmaker,
)
from sqlalchemy.orm import DeclarativeBase


DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://search_user:search_password@db:5432/search_db",
)

# Создаем асинхронный движок
engine = create_async_engine(
    DATABASE_URL,
    echo=True,
    pool_size=20,         # Базовое количество постоянных соединений в пуле
    max_overflow=10,      # Сколько дополнительных соединений можно открыть при пиковой нагрузке
    pool_timeout=30       # Сколько секунд ждать свободное соединение из пула до генерации ошибки
)

async_session = async_sessionmaker(
    bind=engine, class_=AsyncSession, expire_on_commit=False
)


class Base(DeclarativeBase):
    pass


async def get_db():
    async with async_session() as session:
        yield session
