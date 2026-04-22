"""Auth API endpoints."""

from datetime import datetime

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.api.deps import DBSession, CurrentUser, get_user_info
from app.core.security import verify_password, create_token, decode_token
from app.core.config import settings
from app.models.user import User
from app.models.tenant import Tenant
from app.models.log import AuditLog
from app.schemas import (
    BaseResponse,
    LoginRequest,
    LoginResponse,
    RefreshTokenRequest,
    UserInfoResponse,
)
from app.utils.id import generate_id

router = APIRouter()


@router.post("/login", response_model=BaseResponse[LoginResponse])
async def login(request: LoginRequest, db: DBSession):
    """Login endpoint."""
    # Find user by username
    result = await db.execute(select(User).where(User.username == request.username))
    user = result.scalar_one_or_none()
    
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )
    
    # Verify password
    if not verify_password(request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )
    
    # Check user status
    if user.status != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is not active",
        )
    
    # Get tenant info
    tenant_result = await db.execute(select(Tenant).where(Tenant.id == user.tenant_id))
    tenant = tenant_result.scalar_one_or_none()
    
    # Check tenant status
    if tenant and tenant.status != "enabled":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenant is not enabled",
        )
    
    # Create tokens
    access_token = create_token(
        {"sub": user.id, "role": user.role, "tenant_id": user.tenant_id},
        expires_delta=settings.JWT_ACCESS_TOKEN_EXPIRES,
    )
    refresh_token = create_token(
        {"sub": user.id, "type": "refresh"},
        expires_delta=settings.JWT_REFRESH_TOKEN_EXPIRES,
    )
    
    # Update last login time
    user.last_login_at = datetime.utcnow()
    await db.commit()
    
    # Create audit log
    audit_log = AuditLog(
        id=generate_id(),
        tenant_id=user.tenant_id,
        operator_id=user.id,
        operator_name=user.username,
        module="auth",
        action="login",
        target_type="user",
        target_id=user.id,
    )
    db.add(audit_log)
    await db.commit()
    
    # Build response
    user_info = get_user_info(user, tenant)
    
    return BaseResponse(
        data=LoginResponse(
            accessToken=access_token,
            refreshToken=refresh_token,
            expiresIn=settings.JWT_ACCESS_TOKEN_EXPIRES_SECONDS,
            userInfo=user_info,
        )
    )


@router.post("/refresh", response_model=BaseResponse[UserInfoResponse])
async def refresh_token(request: RefreshTokenRequest, db: DBSession):
    """Refresh access token."""
    payload = decode_token(request.refresh_token)
    
    if payload is None or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )
    
    user_id = payload.get("sub")
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if user is None or user.status != "active":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )
    
    # Get tenant
    tenant_result = await db.execute(select(Tenant).where(Tenant.id == user.tenant_id))
    tenant = tenant_result.scalar_one_or_none()
    
    # Create new access token
    access_token = create_token(
        {"sub": user.id, "role": user.role, "tenant_id": user.tenant_id},
        expires_delta=settings.JWT_ACCESS_TOKEN_EXPIRES,
    )
    
    return BaseResponse(
        data=UserInfoResponse(
            accessToken=access_token,
            expiresIn=settings.JWT_ACCESS_TOKEN_EXPIRES_SECONDS,
        )
    )


@router.get("/me", response_model=BaseResponse[UserInfoResponse])
async def get_me(current_user: CurrentUser, db: DBSession):
    """Get current user info."""
    tenant_result = await db.execute(select(Tenant).where(Tenant.id == current_user.tenant_id))
    tenant = tenant_result.scalar_one_or_none()
    
    user_info = get_user_info(current_user, tenant)
    return BaseResponse(data=user_info)


@router.post("/logout", response_model=BaseResponse)
async def logout(current_user: CurrentUser, db: DBSession):
    """Logout endpoint."""
    # Create audit log
    audit_log = AuditLog(
        id=generate_id(),
        tenant_id=current_user.tenant_id,
        operator_id=current_user.id,
        operator_name=current_user.username,
        module="auth",
        action="logout",
        target_type="user",
        target_id=current_user.id,
    )
    db.add(audit_log)
    await db.commit()
    
    return BaseResponse(message="Logged out successfully")