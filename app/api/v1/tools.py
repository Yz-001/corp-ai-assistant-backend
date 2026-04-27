"""Tool management API endpoints."""

from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import select, func

from app.api.deps import DBSession, TenantAdmin
from app.models.tool import ToolDefinition, TenantToolPermission, ToolCallLog
from app.schemas import (
    BaseResponse,
    PaginatedResponse,
    ToolCreate,
    ToolUpdate,
    ToolResponse,
    ToolListResponse,
    ToolStatsResponse,
)
from app.utils.id import generate_id

router = APIRouter()


@router.get("", response_model=BaseResponse[PaginatedResponse[ToolListResponse]])
async def list_tools(
    db: DBSession,
    current_user: TenantAdmin,
    pageNum: int = Query(1, ge=1),
    pageSize: int = Query(20, ge=1),
    status: str | None = Query(None),
    type: str | None = Query(None),
):
    """List all tools."""
    query = select(ToolDefinition)
    
    if status:
        query = query.where(ToolDefinition.status == status)
    if type:
        query = query.where(ToolDefinition.type == type)
    
    # Get all tools first (for stats calculation)
    result = await db.execute(query.order_by(ToolDefinition.created_at.desc()))
    tools = result.scalars().all()
    
    # Enrich with stats
    enriched = []
    for t in tools:
        # Get call stats
        call_stats = await db.execute(
            select(
                func.count().label("total"),
                func.avg(ToolCallLog.latency_ms).label("avg_latency"),
            ).where(ToolCallLog.tool_id == t.id)
        )
        stats = call_stats.first()
        
        # Get error count
        error_count = await db.execute(
            select(func.count()).where(
                ToolCallLog.tool_id == t.id,
                ToolCallLog.status == "failed"
            )
        )
        errors = error_count.scalar() or 0
        total = stats.total or 0
        
        enriched.append(ToolListResponse(
            toolId=t.id,
            code=t.code,
            name=t.name,
            type=t.type,
            description=t.description,
            status=t.status,
            healthStatus=t.health_status,
            callCount=total,
            avgLatencyMs=round(stats.avg_latency or 0),
            errorRate=round(errors / total * 100, 2) if total > 0 else 0,
        ))
    
    # Paginate
    total = len(enriched)
    start = (pageNum - 1) * pageSize
    items = enriched[start:start + pageSize]
    
    return BaseResponse(
        data=PaginatedResponse(items=items, total=total, pageNum=pageNum, pageSize=pageSize)
    )


@router.post("", response_model=BaseResponse[ToolResponse])
async def create_tool(
    request: ToolCreate,
    db: DBSession,
    current_user: TenantAdmin,
):
    """Create a new tool."""
    # Check if code exists
    existing = await db.execute(select(ToolDefinition).where(ToolDefinition.code == request.code))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="工具编码已存在")
    
    tool = ToolDefinition(
        id=generate_id(),
        code=request.code,
        name=request.name,
        type=request.type,
        description=request.description or "",
        config=request.config or {},
        status="active",
        health_status="healthy",
    )
    db.add(tool)
    await db.commit()
    await db.refresh(tool)
    
    return BaseResponse(
        data=ToolResponse(
            toolId=tool.id,
            code=tool.code,
            name=tool.name,
            type=tool.type,
            description=tool.description,
            status=tool.status,
            healthStatus=tool.health_status,
            config=tool.config,
            createdAt=tool.created_at,
            updatedAt=tool.updated_at,
        ),
        message="创建成功",
    )


@router.get("/{toolId}", response_model=BaseResponse[ToolResponse])
async def get_tool(
    toolId: str,
    db: DBSession,
    current_user: TenantAdmin,
):
    """Get tool details."""
    result = await db.execute(select(ToolDefinition).where(ToolDefinition.id == toolId))
    tool = result.scalar_one_or_none()
    
    if not tool:
        raise HTTPException(status_code=404, detail="工具不存在")
    
    return BaseResponse(
        data=ToolResponse(
            toolId=tool.id,
            code=tool.code,
            name=tool.name,
            type=tool.type,
            description=tool.description,
            status=tool.status,
            healthStatus=tool.health_status,
            config=tool.config,
            createdAt=tool.created_at,
            updatedAt=tool.updated_at,
        )
    )


@router.patch("/{toolId}", response_model=BaseResponse[ToolResponse])
async def update_tool(
    toolId: str,
    request: ToolUpdate,
    db: DBSession,
    current_user: TenantAdmin,
):
    """Update tool."""
    result = await db.execute(select(ToolDefinition).where(ToolDefinition.id == toolId))
    tool = result.scalar_one_or_none()
    
    if not tool:
        raise HTTPException(status_code=404, detail="工具不存在")
    
    if request.name:
        tool.name = request.name
    if request.description:
        tool.description = request.description
    if request.config:
        tool.config = request.config
    
    await db.commit()
    await db.refresh(tool)
    
    return BaseResponse(
        data=ToolResponse(
            toolId=tool.id,
            code=tool.code,
            name=tool.name,
            type=tool.type,
            description=tool.description,
            status=tool.status,
            healthStatus=tool.health_status,
            config=tool.config,
            createdAt=tool.created_at,
            updatedAt=tool.updated_at,
        )
    )


@router.patch("/{toolId}/status", response_model=BaseResponse[ToolResponse])
async def update_tool_status(
    toolId: str,
    status: str = Query(..., description="New status: active or inactive"),
    db: DBSession = None,
    current_user: TenantAdmin = None,
):
    """Update tool status."""
    result = await db.execute(select(ToolDefinition).where(ToolDefinition.id == toolId))
    tool = result.scalar_one_or_none()
    
    if not tool:
        raise HTTPException(status_code=404, detail="工具不存在")
    
    tool.status = status
    await db.commit()
    await db.refresh(tool)
    
    return BaseResponse(
        data=ToolResponse(
            toolId=tool.id,
            code=tool.code,
            name=tool.name,
            type=tool.type,
            description=tool.description,
            status=tool.status,
            healthStatus=tool.health_status,
            config=tool.config,
            createdAt=tool.created_at,
            updatedAt=tool.updated_at,
        )
    )


@router.post("/{toolId}/permissions", response_model=BaseResponse)
async def grant_tool_permission(
    toolId: str,
    tenantIds: list[str] = Query(..., description="List of tenant IDs to grant permission"),
    db: DBSession = DBSession,
    current_user: TenantAdmin = TenantAdmin,
):
    """Grant tool permission to tenants (super admin only)."""
    from app.models.tool import TenantToolPermission
    from app.models.tenant import Tenant
    
    # Only super admin can grant permissions
    if current_user.role != "super_admin":
        raise HTTPException(status_code=403, detail="只有超级管理员可以授权工具")
    
    # Verify tool exists
    result = await db.execute(select(ToolDefinition).where(ToolDefinition.id == toolId))
    tool = result.scalar_one_or_none()
    
    if not tool:
        raise HTTPException(status_code=404, detail="工具不存在")
    
    # Verify all tenants exist
    for tenant_id in tenantIds:
        tenant_result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
        if not tenant_result.scalar_one_or_none():
            raise HTTPException(status_code=404, detail=f"租户 {tenant_id} 不存在")
    
    # Create or update permissions
    granted_count = 0
    for tenant_id in tenantIds:
        # Check if permission already exists
        existing = await db.execute(
            select(TenantToolPermission).where(
                TenantToolPermission.tool_id == toolId,
                TenantToolPermission.tenant_id == tenant_id,
            )
        )
        perm = existing.scalar_one_or_none()
        
        if perm:
            # Update existing permission
            if not perm.enabled:
                perm.enabled = True
                granted_count += 1
        else:
            # Create new permission
            perm = TenantToolPermission(
                id=generate_id(),
                tool_id=toolId,
                tenant_id=tenant_id,
                enabled=True,
            )
            db.add(perm)
            granted_count += 1
    
    await db.commit()
    
    return BaseResponse(message=f"已为 {granted_count} 个租户授权工具")


@router.delete("/{toolId}/permissions", response_model=BaseResponse)
async def revoke_tool_permission(
    toolId: str,
    tenantIds: list[str] = Query(..., description="List of tenant IDs to revoke permission"),
    db: DBSession = DBSession,
    current_user: TenantAdmin = TenantAdmin,
):
    """Revoke tool permission from tenants (super admin only)."""
    from app.models.tool import TenantToolPermission
    
    # Only super admin can revoke permissions
    if current_user.role != "super_admin":
        raise HTTPException(status_code=403, detail="只有超级管理员可以撤销工具授权")
    
    # Verify tool exists
    result = await db.execute(select(ToolDefinition).where(ToolDefinition.id == toolId))
    tool = result.scalar_one_or_none()
    
    if not tool:
        raise HTTPException(status_code=404, detail="工具不存在")
    
    # Revoke permissions
    revoked_count = 0
    for tenant_id in tenantIds:
        result = await db.execute(
            select(TenantToolPermission).where(
                TenantToolPermission.tool_id == toolId,
                TenantToolPermission.tenant_id == tenant_id,
            )
        )
        perm = result.scalar_one_or_none()
        
        if perm and perm.enabled:
            perm.enabled = False
            revoked_count += 1
    
    await db.commit()
    
    return BaseResponse(message=f"已撤销 {revoked_count} 个租户的工具授权")


@router.get("/{toolId}/permissions", response_model=BaseResponse[list])
async def get_tool_permissions(
    toolId: str,
    db: DBSession,
    current_user: TenantAdmin,
):
    """Get tool permissions for all tenants."""
    from app.models.tool import TenantToolPermission
    from app.models.tenant import Tenant
    
    # Verify tool exists
    result = await db.execute(select(ToolDefinition).where(ToolDefinition.id == toolId))
    tool = result.scalar_one_or_none()
    
    if not tool:
        raise HTTPException(status_code=404, detail="工具不存在")
    
    # Get all permissions with tenant info
    result = await db.execute(
        select(TenantToolPermission, Tenant)
        .join(Tenant, TenantToolPermission.tenant_id == Tenant.id)
        .where(TenantToolPermission.tool_id == toolId)
    )
    
    permissions = []
    for perm, tenant in result.all():
        permissions.append({
            "tenantId": tenant.id,
            "tenantName": tenant.name,
            "enabled": perm.enabled,
            "createdAt": perm.created_at,
        })
    
    return BaseResponse(data=permissions)


@router.get("/{toolId}/stats", response_model=BaseResponse[ToolStatsResponse])
async def get_tool_stats(
    toolId: str,
    db: DBSession,
    current_user: TenantAdmin,
):
    """Get tool statistics."""
    result = await db.execute(select(ToolDefinition).where(ToolDefinition.id == toolId))
    tool = result.scalar_one_or_none()
    
    if not tool:
        raise HTTPException(status_code=404, detail="工具不存在")
    
    # Get call stats
    call_stats = await db.execute(
        select(
            func.count().label("total_calls"),
            func.avg(ToolCallLog.latency_ms).label("avg_latency"),
            func.min(ToolCallLog.latency_ms).label("min_latency"),
            func.max(ToolCallLog.latency_ms).label("max_latency"),
        ).where(ToolCallLog.tool_id == toolId)
    )
    stats = call_stats.first()
    
    # Get error count
    error_count = await db.execute(
        select(func.count()).where(
            ToolCallLog.tool_id == toolId,
            ToolCallLog.status == "failed"
        )
    )
    errors = error_count.scalar() or 0
    total = stats.total_calls or 0
    
    return BaseResponse(
        data=ToolStatsResponse(
            toolId=tool.id,
            totalCalls=total,
            avgLatencyMs=round(stats.avg_latency or 0),
            minLatencyMs=round(stats.min_latency or 0),
            maxLatencyMs=round(stats.max_latency or 0),
            errorCount=errors,
            errorRate=round(errors / total * 100, 2) if total > 0 else 0,
        )
    )