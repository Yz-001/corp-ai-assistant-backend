from __future__ import annotations

"""User management API endpoints."""

from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from app.api.deps import DBSession, CurrentUser, TenantAdmin, SuperAdmin
from app.models.user import User
from app.models.tenant import Tenant
from app.schemas import BaseResponse, PaginatedResponse
from app.schemas.user import UserCreate, UserUpdate, UserPasswordUpdate, UserResponse, UserListResponse
from app.utils.id import generate_id
from app.core.security import get_password_hash, verify_password

router = APIRouter()


@router.get("", response_model=BaseResponse[PaginatedResponse[UserListResponse]])
async def list_users(
    db: DBSession,
    current_user: TenantAdmin,
    pageNum: int = Query(1, ge=1),
    pageSize: int = Query(20, ge=1, le=100),
    role: str | None = Query(None),
    status: str | None = Query(None),
    keyword: str | None = Query(None),
):
    """List users with pagination and filters."""
    query = select(User).options(selectinload(User.tenant))
    
    # Non-super-admin can only see users in their tenant
    if not current_user.is_super_admin:
        query = query.where(User.tenant_id == current_user.tenant_id)
    
    if role:
        query = query.where(User.role == role)
    if status:
        query = query.where(User.status == status)
    if keyword:
        query = query.where(
            (User.username.ilike(f"%{keyword}%")) | 
            (User.email.ilike(f"%{keyword}%"))
        )
    
    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # Get paginated results
    query = query.order_by(User.created_at.desc())
    query = query.offset((pageNum - 1) * pageSize).limit(pageSize)
    
    result = await db.execute(query)
    users = result.scalars().all()
    
    items = [
        UserListResponse(
            userId=u.id,
            username=u.username,
            email=u.email,
            role=u.role,
            status=u.status,
            tenantId=u.tenant_id,
            tenantName=u.tenant.name if u.tenant else None,
            lastLoginAt=u.last_login_at,
            createdAt=u.created_at,
        )
        for u in users
    ]
    
    return BaseResponse(
        data=PaginatedResponse(items=items, total=total, pageNum=pageNum, pageSize=pageSize)
    )


@router.post("", response_model=BaseResponse[UserResponse])
async def create_user(
    request: UserCreate,
    db: DBSession,
    current_user: TenantAdmin,
):
    """Create a new user."""
    # Check permissions
    if not current_user.is_super_admin:
        # Non-super-admin can only create users in their tenant
        if request.tenant_id != current_user.tenant_id:
            raise HTTPException(status_code=403, detail="无权在该租户下创建用户")
        # Non-super-admin cannot create super_admin or tenant_admin
        if request.role in ("super_admin", "tenant_admin"):
            raise HTTPException(status_code=403, detail="无权创建该角色的用户")
    
    # Check if username exists
    existing = await db.execute(select(User).where(User.username == request.username))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="用户名已存在")
    
    # Check if email exists
    if request.email:
        existing = await db.execute(select(User).where(User.email == request.email))
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="邮箱已被使用")
    
    # Verify tenant exists
    tenant_result = await db.execute(select(Tenant).where(Tenant.id == request.tenant_id))
    tenant = tenant_result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=404, detail="租户不存在")
    
    user = User(
        id=generate_id(),
        tenant_id=request.tenant_id,
        username=request.username,
        email=request.email,
        password_hash=get_password_hash(request.password),
        role=request.role,
        status="enabled",
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    
    return BaseResponse(
        data=UserResponse(
            userId=user.id,
            username=user.username,
            email=user.email,
            role=user.role,
            status=user.status,
            tenantId=user.tenant_id,
            tenantName=tenant.name,
            lastLoginAt=user.last_login_at,
            createdAt=user.created_at,
            updatedAt=user.updated_at,
        ),
        message="创建成功",
    )


@router.get("/me", response_model=BaseResponse[UserResponse])
async def get_current_user_info(
    db: DBSession,
    current_user: CurrentUser,
):
    """Get current user information."""
    user = current_user
    
    # Get tenant name
    tenant_result = await db.execute(select(Tenant).where(Tenant.id == user.tenant_id))
    tenant = tenant_result.scalar_one_or_none()
    
    return BaseResponse(
        data=UserResponse(
            userId=user.id,
            username=user.username,
            email=user.email,
            role=user.role,
            status=user.status,
            tenantId=user.tenant_id,
            tenantName=tenant.name if tenant else None,
            lastLoginAt=user.last_login_at,
            createdAt=user.created_at,
            updatedAt=user.updated_at,
        )
    )


@router.get("/{userId}", response_model=BaseResponse[UserResponse])
async def get_user(
    userId: str,
    db: DBSession,
    current_user: TenantAdmin,
):
    """Get user details."""
    result = await db.execute(
        select(User).options(selectinload(User.tenant)).where(User.id == userId)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    # Non-super-admin can only see users in their tenant
    if not current_user.is_super_admin and user.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=403, detail="无权查看该用户")
    
    return BaseResponse(
        data=UserResponse(
            userId=user.id,
            username=user.username,
            email=user.email,
            role=user.role,
            status=user.status,
            tenantId=user.tenant_id,
            tenantName=user.tenant.name if user.tenant else None,
            lastLoginAt=user.last_login_at,
            createdAt=user.created_at,
            updatedAt=user.updated_at,
        )
    )


@router.patch("/{userId}", response_model=BaseResponse[UserResponse])
async def update_user(
    userId: str,
    request: UserUpdate,
    db: DBSession,
    current_user: TenantAdmin,
):
    """Update user information."""
    result = await db.execute(
        select(User).options(selectinload(User.tenant)).where(User.id == userId)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    # Non-super-admin can only update users in their tenant
    if not current_user.is_super_admin and user.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=403, detail="无权修改该用户")
    
    # Non-super-admin cannot change role to super_admin or tenant_admin
    if request.role and not current_user.is_super_admin:
        if request.role in ("super_admin", "tenant_admin"):
            raise HTTPException(status_code=403, detail="无权设置该角色")
    
    if request.email:
        # Check if email is taken by another user
        existing = await db.execute(
            select(User).where(User.email == request.email, User.id != userId)
        )
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="邮箱已被使用")
        user.email = request.email
    
    if request.role:
        user.role = request.role
    
    if request.status:
        user.status = request.status
    
    await db.commit()
    await db.refresh(user)
    
    return BaseResponse(
        data=UserResponse(
            userId=user.id,
            username=user.username,
            email=user.email,
            role=user.role,
            status=user.status,
            tenantId=user.tenant_id,
            tenantName=user.tenant.name if user.tenant else None,
            lastLoginAt=user.last_login_at,
            createdAt=user.created_at,
            updatedAt=user.updated_at,
        ),
        message="更新成功",
    )


@router.patch("/{userId}/password", response_model=BaseResponse)
async def update_user_password(
    userId: str,
    request: UserPasswordUpdate,
    db: DBSession,
    current_user: CurrentUser,
):
    """Update user password."""
    # Users can only change their own password (or admin can change any)
    if current_user.id != userId and not current_user.is_tenant_admin and not current_user.is_super_admin:
        raise HTTPException(status_code=403, detail="无权修改该用户密码")
    
    result = await db.execute(select(User).where(User.id == userId))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    # If changing own password, verify old password
    if current_user.id == userId:
        if not verify_password(request.old_password, user.password_hash):
            raise HTTPException(status_code=400, detail="原密码错误")
    
    user.password_hash = get_password_hash(request.new_password)
    await db.commit()
    
    return BaseResponse(message="密码修改成功")


@router.patch("/{userId}/status", response_model=BaseResponse[UserResponse])
async def update_user_status(
    userId: str,
    status: str = Query(..., description="New status: enabled or disabled"),
    db: DBSession = None,
    current_user: TenantAdmin = None,
):
    """Update user status (enable/disable)."""
    result = await db.execute(
        select(User).options(selectinload(User.tenant)).where(User.id == userId)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    # Non-super-admin can only update users in their tenant
    if not current_user.is_super_admin and user.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=403, detail="无权修改该用户")
    
    # Cannot disable super_admin unless you are super_admin
    if user.is_super_admin and not current_user.is_super_admin:
        raise HTTPException(status_code=403, detail="无权修改超级管理员状态")
    
    user.status = status
    await db.commit()
    await db.refresh(user)
    
    return BaseResponse(
        data=UserResponse(
            userId=user.id,
            username=user.username,
            email=user.email,
            role=user.role,
            status=user.status,
            tenantId=user.tenant_id,
            tenantName=user.tenant.name if user.tenant else None,
            lastLoginAt=user.last_login_at,
            createdAt=user.created_at,
            updatedAt=user.updated_at,
        ),
        message="状态更新成功",
    )


@router.delete("/{userId}", response_model=BaseResponse)
async def delete_user(
    userId: str,
    db: DBSession,
    current_user: TenantAdmin,
):
    """Delete a user."""
    result = await db.execute(select(User).where(User.id == userId))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    # Non-super-admin can only delete users in their tenant
    if not current_user.is_super_admin and user.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=403, detail="无权删除该用户")
    
    # Cannot delete super_admin unless you are super_admin
    if user.is_super_admin and not current_user.is_super_admin:
        raise HTTPException(status_code=403, detail="无权删除超级管理员")
    
    # Cannot delete yourself
    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="不能删除自己")
    
    await db.delete(user)
    await db.commit()
    
    return BaseResponse(message="删除成功")
