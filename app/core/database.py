"""Database configuration and session management."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings


class Base(DeclarativeBase):
    """Base class for all database models."""

    pass


def create_engine() -> AsyncEngine:
    """Create async database engine."""
    # Convert postgres:// to postgresql+asyncpg://
    url = settings.database_url
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://")
    elif url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+asyncpg://")

    return create_async_engine(
        url,
        echo=settings.db_echo,
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,
    )


engine = create_engine()
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for getting database session."""
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@asynccontextmanager
async def get_db_context() -> AsyncGenerator[AsyncSession, None]:
    """Context manager for database session."""
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """Initialize database tables and create default data."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Create default tenant and admin user if not exists
    async with async_session_maker() as session:
        from sqlalchemy import select
        from app.models.tenant import Tenant
        from app.models.user import User
        from app.core.security import get_password_hash
        from app.utils.id import generate_id
        
        # Check if default tenant exists
        result = await session.execute(
            select(Tenant).where(Tenant.id == "default")
        )
        tenant = result.scalar_one_or_none()
        
        if not tenant:
            # Create default tenant
            tenant = Tenant(
                id="default",
                name="Default Tenant",
                code="default",
                type="enterprise",
                status="enabled",
                plan_type="enterprise",
            )
            session.add(tenant)
            await session.flush()
        
        # Check if admin user exists
        result = await session.execute(
            select(User).where(User.username == "admin")
        )
        user = result.scalar_one_or_none()
        
        if not user:
            # Create admin user
            user = User(
                id=generate_id(),
                tenant_id="default",
                username="admin",
                password_hash=get_password_hash("admin123"),
                email="admin@example.com",
                role="super_admin",
                status="enabled",
            )
            session.add(user)
            await session.commit()
            print("Created default admin user: admin / admin123")


async def close_db() -> None:
    """Close database connections."""
    await engine.dispose()