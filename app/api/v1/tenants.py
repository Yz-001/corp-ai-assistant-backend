"""Tenant management API endpoints."""

from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import select, func

from app.api.deps import DBSession, SuperUser, TenantAdmin
from app.models.tenant import Tenant
from app.models.user import User
from app.models.document import Document
from app.models.usage import UsageRecord
from app.schemas import (
    BaseResponse,
    PaginatedResponse,
    TenantCreate,
    TenantUpdate,
    TenantResponse,
    TenantListResponse,
    TenantUsageResponse,
)
from app.utils.id import generate_id

router = APIRouter()


@router.get("", response_model=BaseResponse[PaginatedResponse[TenantListResponse]])
async def list_tenants(
    db: DBSession,
    current_user: SuperUser,
    pageNum: int = Query(1, ge=1),
    pageSize: int = Query(20, ge=1, le=100),
    keyword: str | None = Query(None),
    status: str | None = Query(None),
    type: str | None = Query(None),
):
    """List all tenants (super admin only)."""
    query = select(Tenant)
    
    if keyword:
        query = query.where(
            (Tenant.name.ilike(f"%{keyword}%")) | 
            (Tenant.code.ilike(f"%{keyword}%"))
        )
    if status:
        query = query.where(Tenant.status == status)
    if type:
        query = query.where(Tenant.type == type)
    
    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # Get paginated results
    query = query.order_by(Tenant.created_at.desc())
    query = query.offset((pageNum - 1) * pageSize).limit(pageSize)
    
    result = await db.execute(query)
    tenants = result.scalars().all()
    
    # Enrich with counts
    items = []
    for t in tenants:
        # Get user count
        user_count_result = await db.execute(
            select(func.count()).select_from(User).where(User.tenant_id == t.id)
        )
        user_count = user_count_result.scalar() or 0
        
        # Get document count
        doc_count_result = await db.execute(
            select(func.count()).select_from(Document).where(Document.tenant_id == t.id)
        )
        doc_count = doc_count_result.scalar() or 0
        
        # Get usage stats
        request_agg = await db.execute(
            select(func.sum(UsageRecord.request_count)).where(UsageRecord.tenant_id == t.id)
        )
        request_count = request_agg.scalar() or 0
        
        token_agg = await db.execute(
            select(func.sum(UsageRecord.token_count)).where(UsageRecord.tenant_id == t.id)
        )
        token_count = token_agg.scalar() or 0
        
        items.append(TenantListResponse(
            tenantId=t.id,
            name=t.name,
            code=t.code,
            type=t.type,
            planType=t.plan_type,
            status=t.status,
            userCount=user_count,
            documentCount=doc_count,
            requestCount=request_count,
            tokenCount=token_count,
            createdAt=t.created_at,
            updatedAt=t.updated_at,
        ))
    
    return BaseResponse(
        data=PaginatedResponse(list=items, total=total, pageNum=pageNum, pageSize=pageSize)
    )


@router.post("", response_model=BaseResponse[TenantResponse])
async def create_tenant(
    request: TenantCreate,
    db: DBSession,
    current_user: SuperUser,
):
    """Create a new tenant (super admin only)."""
    # Check if code exists
    existing = await db.execute(select(Tenant).where(Tenant.code == request.code))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="租户编码已存在")
    
    tenant = Tenant(
        id=generate_id(),
        name=request.name,
        code=request.code,
        type=request.type or "enterprise",
        plan_type=request.planType or "basic",
        status=request.status or "enabled",
        quota_config=request.quotaConfig or {},
    )
    db.add(tenant)
    await db.commit()
    await db.refresh(tenant)
    
    return BaseResponse(
        data=TenantResponse(
            tenantId=tenant.id,
            name=tenant.name,
            code=tenant.code,
            type=tenant.type,
            planType=tenant.plan_type,
            status=tenant.status,
            quotaConfig=tenant.quota_config,
            createdAt=tenant.created_at,
            updatedAt=tenant.updated_at,
        ),
        message="创建成功",
    )


@router.get("/{tenantId}", response_model=BaseResponse[TenantResponse])
async def get_tenant(
    tenantId: str,
    db: DBSession,
    current_user: TenantAdmin,
):
    """Get tenant details."""
    result = await db.execute(select(Tenant).where(Tenant.id == tenantId))
    tenant = result.scalar_one_or_none()
    
    if not tenant:
        raise HTTPException(status_code=404, detail="租户不存在")
    
    # Check permission for tenant admin
    if current_user.role != "super_admin" and current_user.tenant_id != tenantId:
        raise HTTPException(status_code=403, detail="无权限访问此租户")
    
    return BaseResponse(
        data=TenantResponse(
            tenantId=tenant.id,
            name=tenant.name,
            code=tenant.code,
            type=tenant.type,
            planType=tenant.plan_type,
            status=tenant.status,
            quotaConfig=tenant.quota_config,
            createdAt=tenant.created_at,
            updatedAt=tenant.updated_at,
        )
    )


@router.patch("/{tenantId}", response_model=BaseResponse[TenantResponse])
async def update_tenant(
    tenantId: str,
    request: TenantUpdate,
    db: DBSession,
    current_user: SuperUser,
):
    """Update tenant (super admin only)."""
    result = await db.execute(select(Tenant).where(Tenant.id == tenantId))
    tenant = result.scalar_one_or_none()
    
    if not tenant:
        raise HTTPException(status_code=404, detail="租户不存在")
    
    if request.name:
        tenant.name = request.name
    if request.planType:
        tenant.plan_type = request.planType
    if request.quotaConfig:
        tenant.quota_config = request.quota_config
    
    await db.commit()
    await db.refresh(tenant)
    
    return BaseResponse(
        data=TenantResponse(
            tenantId=tenant.id,
            name=tenant.name,
            code=tenant.code,
            type=tenant.type,
            planType=tenant.plan_type,
            status=tenant.status,
            quotaConfig=tenant.quota_config,
            createdAt=tenant.created_at,
            updatedAt=tenant.updated_at,
        )
    )


@router.patch("/{tenantId}/status", response_model=BaseResponse[TenantResponse])
async def update_tenant_status(
    tenantId: str,
    status: str = Query(..., description="New status: enabled or disabled"),
    db: DBSession = None,
    current_user: SuperUser = None,
):
    """Update tenant status (super admin only)."""
    result = await db.execute(select(Tenant).where(Tenant.id == tenantId))
    tenant = result.scalar_one_or_none()
    
    if not tenant:
        raise HTTPException(status_code=404, detail="租户不存在")
    
    tenant.status = status
    await db.commit()
    await db.refresh(tenant)
    
    return BaseResponse(
        data=TenantResponse(
            tenantId=tenant.id,
            name=tenant.name,
            code=tenant.code,
            type=tenant.type,
            planType=tenant.plan_type,
            status=tenant.status,
            quotaConfig=tenant.quota_config,
            createdAt=tenant.created_at,
            updatedAt=tenant.updated_at,
        )
    )


@router.get("/{tenantId}/usage", response_model=BaseResponse[TenantUsageResponse])
async def get_tenant_usage(
    tenantId: str,
    db: DBSession,
    current_user: TenantAdmin,
):
    """Get tenant usage statistics."""
    result = await db.execute(select(Tenant).where(Tenant.id == tenantId))
    tenant = result.scalar_one_or_none()
    
    if not tenant:
        raise HTTPException(status_code=404, detail="租户不存在")
    
    # Check permission for tenant admin
    if current_user.role != "super_admin" and current_user.tenant_id != tenantId:
        raise HTTPException(status_code=403, detail="无权限访问此租户")
    
    # Get usage stats
    request_agg = await db.execute(
        select(func.sum(UsageRecord.request_count)).where(UsageRecord.tenant_id == tenantId)
    )
    total_requests = request_agg.scalar() or 0
    
    token_agg = await db.execute(
        select(func.sum(UsageRecord.token_count)).where(UsageRecord.tenant_id == tenantId)
    )
    total_tokens = token_agg.scalar() or 0
    
    # Get user count
    user_count_result = await db.execute(
        select(func.count()).select_from(User).where(User.tenant_id == tenantId)
    )
    user_count = user_count_result.scalar() or 0
    
    # Get document count
    doc_count_result = await db.execute(
        select(func.count()).select_from(Document).where(Document.tenant_id == tenantId)
    )
    doc_count = doc_count_result.scalar() or 0
    
    return BaseResponse(
        data=TenantUsageResponse(
            tenantId=tenant.id,
            totalRequests=total_requests,
            totalTokens=total_tokens,
            userCount=user_count,
            documentCount=doc_count,
        )
    )
