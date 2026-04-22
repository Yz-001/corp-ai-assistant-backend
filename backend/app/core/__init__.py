"""Core module initialization."""

from app.core.config import Settings, get_settings, settings
from app.core.database import Base, async_session_maker, engine, get_db, init_db, close_db
from app.core.exceptions import (
    AppException,
    BadRequestException,
    ConflictException,
    ForbiddenException,
    NotFoundException,
    ServerException,
    UnauthorizedException,
    ValidationException,
)
from app.core.redis import redis_client, get_redis, close_redis
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_password_hash,
    verify_password,
    verify_access_token,
    verify_refresh_token,
)

__all__ = [
    # Config
    "Settings",
    "get_settings",
    "settings",
    # Database
    "Base",
    "engine",
    "async_session_maker",
    "get_db",
    "init_db",
    "close_db",
    # Redis
    "redis_client",
    "get_redis",
    "close_redis",
    # Security
    "create_access_token",
    "create_refresh_token",
    "decode_token",
    "get_password_hash",
    "verify_password",
    "verify_access_token",
    "verify_refresh_token",
    # Exceptions
    "AppException",
    "BadRequestException",
    "ConflictException",
    "ForbiddenException",
    "NotFoundException",
    "ServerException",
    "UnauthorizedException",
    "ValidationException",
]