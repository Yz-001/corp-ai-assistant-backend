"""API dependencies."""

from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import decode_token
from app.core.config import settings
from app.models.user import User
from app.models.tenant import Tenant
from app.schemas.auth import UserInfoResponse

security = HTTPBearer()


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    """Get current user from token."""
    token = credentials.credentials
    payload = decode_token(token)
    
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )
    
    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )
    
    # Get user from database
    from sqlalchemy import select
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    
    if user.status != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is not active",
        )
    
    return user


async def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """Get current active user."""
    if current_user.status != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user",
        )
    return current_user


def require_role(allowed_roles: list[str]):
    """Require user to have one of the allowed roles."""
    async def role_checker(
        current_user: Annotated[User, Depends(get_current_user)],
    ) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return current_user
    return role_checker


async def get_superuser(
    current_user: Annotated[User, Depends(require_role(["super_admin"]))],
) -> User:
    """Require super admin role."""
    return current_user


async def get_tenant_admin(
    current_user: Annotated[User, Depends(require_role(["super_admin", "tenant_admin"]))],
) -> User:
    """Require tenant admin or super admin role."""
    return current_user


def get_user_info(user: User, tenant: Tenant | None = None) -> UserInfoResponse:
    """Build user info response."""
    # Build permissions based on role
    permissions = []
    if user.role == "super_admin":
        permissions = ["*"]
    elif user.role == "tenant_admin":
        permissions = ["tenant:read", "tenant:write", "document:read", "document:write", "log:read"]
    elif user.role == "tenant_user":
        permissions = ["chat:read", "chat:write", "document:read"]
    elif user.role == "public_user":
        permissions = ["chat:read"]
    
    return UserInfoResponse(
        userId=user.id,
        username=user.username,
        email=user.email,
        role=user.role,
        tenantId=user.tenant_id,
        tenantName=tenant.name if tenant else None,
        permissions=permissions,
    )


# Type aliases for dependency injection
CurrentUser = Annotated[User, Depends(get_current_user)]
ActiveUser = Annotated[User, Depends(get_current_active_user)]
SuperUser = Annotated[User, Depends(get_superuser)]
TenantAdmin = Annotated[User, Depends(get_tenant_admin)]
DBSession = Annotated[AsyncSession, Depends(get_db)]