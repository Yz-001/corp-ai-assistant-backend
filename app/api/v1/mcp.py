"""MCP (Model Context Protocol) management API endpoints."""

from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import select, func

from app.api.deps import DBSession, TenantAdmin
from app.models.mcp import MCPServer, MCPTool
from app.schemas import (
    BaseResponse,
    PaginatedResponse,
    MCPServerCreate,
    MCPServerUpdate,
    MCPServerResponse,
    MCPToolResponse,
)
from app.utils.id import generate_id

router = APIRouter()


# ============ MCP Servers ============


@router.get("/servers", response_model=BaseResponse[PaginatedResponse[MCPServerResponse]])
async def list_mcp_servers(
    db: DBSession,
    current_user: TenantAdmin,
    pageNum: int = Query(1, ge=1),
    pageSize: int = Query(20, ge=1, le=100),
    status: str | None = Query(None),
):
    """List all MCP servers."""
    query = select(MCPServer)
    
    if status:
        query = query.where(MCPServer.status == status)
    
    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # Get paginated results
    query = query.order_by(MCPServer.created_at.desc())
    query = query.offset((pageNum - 1) * pageSize).limit(pageSize)
    
    result = await db.execute(query)
    servers = result.scalars().all()
    
    items = [
        MCPServerResponse(
            serverId=s.id,
            name=s.name,
            transportType=s.transport_type,
            endpoint=s.endpoint,
            status=s.status,
            healthStatus=s.health_status,
            toolCount=s.tool_count,
            lastConnectedAt=s.last_connected_at,
            createdAt=s.created_at,
            updatedAt=s.updated_at,
        )
        for s in servers
    ]
    
    return BaseResponse(
        data=PaginatedResponse(items=items, total=total, pageNum=pageNum, pageSize=pageSize)
    )


@router.post("/servers", response_model=BaseResponse[MCPServerResponse])
async def create_mcp_server(
    request: MCPServerCreate,
    db: DBSession,
    current_user: TenantAdmin,
):
    """Create a new MCP server."""
    server = MCPServer(
        id=generate_id(),
        name=request.name,
        transport_type=request.transportType,
        endpoint=request.endpoint,
        config=request.config or {},
        status="inactive",
        health_status="unknown",
        tool_count=0,
    )
    db.add(server)
    await db.commit()
    await db.refresh(server)
    
    return BaseResponse(
        data=MCPServerResponse(
            serverId=server.id,
            name=server.name,
            transportType=server.transport_type,
            endpoint=server.endpoint,
            status=server.status,
            healthStatus=server.health_status,
            toolCount=server.tool_count,
            lastConnectedAt=server.last_connected_at,
            createdAt=server.created_at,
            updatedAt=server.updated_at,
        ),
        message="创建成功",
    )


@router.get("/servers/{serverId}", response_model=BaseResponse[MCPServerResponse])
async def get_mcp_server(
    serverId: str,
    db: DBSession,
    current_user: TenantAdmin,
):
    """Get MCP server details."""
    result = await db.execute(select(MCPServer).where(MCPServer.id == serverId))
    server = result.scalar_one_or_none()
    
    if not server:
        raise HTTPException(status_code=404, detail="MCP服务器不存在")
    
    return BaseResponse(
        data=MCPServerResponse(
            serverId=server.id,
            name=server.name,
            transportType=server.transport_type,
            endpoint=server.endpoint,
            status=server.status,
            healthStatus=server.health_status,
            toolCount=server.tool_count,
            lastConnectedAt=server.last_connected_at,
            createdAt=server.created_at,
            updatedAt=server.updated_at,
        )
    )


@router.patch("/servers/{serverId}", response_model=BaseResponse[MCPServerResponse])
async def update_mcp_server(
    serverId: str,
    request: MCPServerUpdate,
    db: DBSession,
    current_user: TenantAdmin,
):
    """Update MCP server."""
    result = await db.execute(select(MCPServer).where(MCPServer.id == serverId))
    server = result.scalar_one_or_none()
    
    if not server:
        raise HTTPException(status_code=404, detail="MCP服务器不存在")
    
    if request.name:
        server.name = request.name
    if request.endpoint:
        server.endpoint = request.endpoint
    if request.config:
        server.config = request.config
    
    await db.commit()
    await db.refresh(server)
    
    return BaseResponse(
        data=MCPServerResponse(
            serverId=server.id,
            name=server.name,
            transportType=server.transport_type,
            endpoint=server.endpoint,
            status=server.status,
            healthStatus=server.health_status,
            toolCount=server.tool_count,
            lastConnectedAt=server.last_connected_at,
            createdAt=server.created_at,
            updatedAt=server.updated_at,
        )
    )


@router.delete("/servers/{serverId}", response_model=BaseResponse)
async def delete_mcp_server(
    serverId: str,
    db: DBSession,
    current_user: TenantAdmin,
):
    """Delete MCP server."""
    result = await db.execute(select(MCPServer).where(MCPServer.id == serverId))
    server = result.scalar_one_or_none()
    
    if not server:
        raise HTTPException(status_code=404, detail="MCP服务器不存在")
    
    # Delete associated tools first
    await db.execute(
        select(MCPTool).where(MCPTool.server_id == serverId)
    )
    # In production, you would delete these
    
    await db.delete(server)
    await db.commit()
    
    return BaseResponse(message="删除成功")


@router.get("/servers/{serverId}/status", response_model=BaseResponse[dict])
async def get_mcp_server_status(
    serverId: str,
    db: DBSession,
    current_user: TenantAdmin,
):
    """Get MCP server connection status."""
    result = await db.execute(select(MCPServer).where(MCPServer.id == serverId))
    server = result.scalar_one_or_none()
    
    if not server:
        raise HTTPException(status_code=404, detail="MCP服务器不存在")
    
    # TODO: Implement actual status check
    return BaseResponse(
        data={
            "serverId": server.id,
            "status": server.status,
            "healthStatus": server.health_status,
            "lastConnectedAt": server.last_connected_at,
        }
    )


@router.post("/servers/{serverId}/discover-tools", response_model=BaseResponse[list])
async def discover_mcp_tools(
    serverId: str,
    db: DBSession,
    current_user: TenantAdmin,
):
    """Discover tools from MCP server."""
    result = await db.execute(select(MCPServer).where(MCPServer.id == serverId))
    server = result.scalar_one_or_none()
    
    if not server:
        raise HTTPException(status_code=404, detail="MCP服务器不存在")
    
    # TODO: Implement actual tool discovery via MCP protocol
    # For now, return empty list
    return BaseResponse(data=[], message="工具发现完成")


# ============ MCP Tools ============


@router.get("/tools", response_model=BaseResponse[PaginatedResponse[MCPToolResponse]])
async def list_mcp_tools(
    db: DBSession,
    current_user: TenantAdmin,
    pageNum: int = Query(1, ge=1),
    pageSize: int = Query(20, ge=1, le=100),
    serverId: str | None = Query(None),
):
    """List all MCP tools."""
    query = select(MCPTool)
    
    if serverId:
        query = query.where(MCPTool.server_id == serverId)
    
    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # Get paginated results
    query = query.order_by(MCPTool.created_at.desc())
    query = query.offset((pageNum - 1) * pageSize).limit(pageSize)
    
    result = await db.execute(query)
    tools = result.scalars().all()
    
    items = [
        MCPToolResponse(
            toolId=t.id,
            serverId=t.server_id,
            name=t.name,
            description=t.description,
            inputSchema=t.input_schema,
            enabled=t.enabled,
            createdAt=t.created_at,
        )
        for t in tools
    ]
    
    return BaseResponse(
        data=PaginatedResponse(items=items, total=total, pageNum=pageNum, pageSize=pageSize)
    )


@router.post("/tools/{toolId}/bind-tenants", response_model=BaseResponse)
async def bind_tool_to_tenants(
    toolId: str,
    tenantIds: list[str],
    db: DBSession,
    current_user: TenantAdmin,
):
    """Bind tool to tenants."""
    # TODO: Implement tenant binding
    return BaseResponse(message="绑定成功")