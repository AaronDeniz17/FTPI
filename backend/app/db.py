from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

DATABASE_URL = "sqlite+aiosqlite:///./finance.db"


class Base(DeclarativeBase):
	pass


engine = create_async_engine(
	DATABASE_URL,
	echo=False,
	future=True,
)

AsyncSessionLocal = async_sessionmaker(
	bind=engine,
	expire_on_commit=False,
	autoflush=False,
	class_=AsyncSession,
)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
	async with AsyncSessionLocal() as session:
		yield session


@asynccontextmanager
async def lifespan(app):  # type: ignore[no-untyped-def]
	# Import models here to ensure metadata is available
	from . import models  # noqa: F401

	async with engine.begin() as conn:
		await conn.run_sync(models.Base.metadata.create_all)
	yield
	# No teardown needed for SQLite
