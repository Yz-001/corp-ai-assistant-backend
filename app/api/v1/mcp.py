"""MCP (Model Context Protocol) management API endpoints."""

import asyncio
import json
import time
from datetime import datetime
from typing import Any

import httpx
from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import select, func

from app.api.deps import DBSession, TenantAdmin
from app.models.mcp import MCPServer, MCPTool
from app.models.tool import ToolDefinition
from app.models.tenant import Tenant
from app.schemas import (
    BaseResponse,
    PaginatedResponse,
    MCPServerCreate,
    MCPServerUpdate,
    MCPServerResponse,
    MCPServerTestResponse,
    MCPToolResponse,
    MCPToolDiscoverResponse,
    MCPToolBindTenantsRequest,
    MCPServerStatusUpdate,
)
from app.utils.id import generate_id

router = APIRouter()


# ============ MCP Servers ============


@router.get("/servers", response_model=BaseResponse[PaginatedResponse[MCPServerResponse]])
async def list_mcp_servers(
    db: DBSession,
    current_user: TenantAdmin,
    pageNum: int = Query(1, ge=1),
    pageSize: int = Query(20, ge=1),
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
    
    # Get tool count for each server
    items = []
    for s in servers:
        tool_count_result = await db.execute(
            select(func.count()).select_from(MCPTool).where(MCPTool.server_id == s.id)
        )
        tool_count = tool_count_result.scalar() or 0
        
        items.append(MCPServerResponse(
            serverId=s.id,
            name=s.name,
            transportType=s.transport_type,
            command=s.command,
            args=s.args,
            env=s.env,
            baseUrl=s.base_url,
            authType=s.auth_type,
            status=s.status,
            timeoutSeconds=s.timeout_seconds,
            description=s.description,
            lastCheckAt=s.last_check_at,
            lastCheckStatus=s.last_check_status,
            toolCount=tool_count,
            createdAt=s.created_at,
            updatedAt=s.updated_at,
        ))
    
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
        transport_type=request.transport_type,
        command=request.command,
        args=request.args,
        env=request.env,
        base_url=request.base_url,
        auth_type=request.auth_type,
        auth_config=request.auth_config,
        timeout_seconds=request.timeout_seconds,
        description=request.description,
        status="enabled",
        last_check_status="unknown",
    )
    db.add(server)
    await db.commit()
    await db.refresh(server)
    
    return BaseResponse(
        data=MCPServerResponse(
            serverId=server.id,
            name=server.name,
            transportType=server.transport_type,
            command=server.command,
            args=server.args,
            env=server.env,
            baseUrl=server.base_url,
            authType=server.auth_type,
            status=server.status,
            timeoutSeconds=server.timeout_seconds,
            description=server.description,
            lastCheckAt=server.last_check_at,
            lastCheckStatus=server.last_check_status,
            toolCount=0,
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
    
    # Get tool count
    tool_count_result = await db.execute(
        select(func.count()).select_from(MCPTool).where(MCPTool.server_id == server.id)
    )
    tool_count = tool_count_result.scalar() or 0
    
    return BaseResponse(
        data=MCPServerResponse(
            serverId=server.id,
            name=server.name,
            transportType=server.transport_type,
            command=server.command,
            args=server.args,
            env=server.env,
            baseUrl=server.base_url,
            authType=server.auth_type,
            status=server.status,
            timeoutSeconds=server.timeout_seconds,
            description=server.description,
            lastCheckAt=server.last_check_at,
            lastCheckStatus=server.last_check_status,
            toolCount=tool_count,
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
    if request.transport_type:
        server.transport_type = request.transport_type
    if request.command:
        server.command = request.command
    if request.args:
        server.args = request.args
    if request.env:
        server.env = request.env
    if request.base_url:
        server.base_url = request.base_url
    if request.auth_type:
        server.auth_type = request.auth_type
    if request.auth_config:
        server.auth_config = request.auth_config
    if request.timeout_seconds:
        server.timeout_seconds = request.timeout_seconds
    if request.description is not None:
        server.description = request.description
    
    await db.commit()
    await db.refresh(server)
    
    # Get tool count
    tool_count_result = await db.execute(
        select(func.count()).select_from(MCPTool).where(MCPTool.server_id == server.id)
    )
    tool_count = tool_count_result.scalar() or 0
    
    return BaseResponse(
        data=MCPServerResponse(
            serverId=server.id,
            name=server.name,
            transportType=server.transport_type,
            command=server.command,
            args=server.args,
            env=server.env,
            baseUrl=server.base_url,
            authType=server.auth_type,
            status=server.status,
            timeoutSeconds=server.timeout_seconds,
            description=server.description,
            lastCheckAt=server.last_check_at,
            lastCheckStatus=server.last_check_status,
            toolCount=tool_count,
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
    from app.models.tool import TenantToolPermission
    
    result = await db.execute(select(MCPServer).where(MCPServer.id == serverId))
    server = result.scalar_one_or_none()
    
    if not server:
        raise HTTPException(status_code=404, detail="MCP服务器不存在")
    
    # Delete associated MCP tools and their ToolDefinitions
    mcp_tools = await db.execute(select(MCPTool).where(MCPTool.server_id == serverId))
    for tool in mcp_tools.scalars().all():
        # Find and delete corresponding ToolDefinition
        tool_def = await db.execute(
            select(ToolDefinition).where(ToolDefinition.code == tool.tool_code)
        )
        td = tool_def.scalar_one_or_none()
        if td:
            # Delete permissions
            perms = await db.execute(
                select(TenantToolPermission).where(TenantToolPermission.tool_id == td.id)
            )
            for perm in perms.scalars().all():
                await db.delete(perm)
            await db.delete(td)
        await db.delete(tool)
    
    await db.delete(server)
    await db.commit()
    
    return BaseResponse(message="删除成功")


@router.post("/servers/{serverId}/test", response_model=BaseResponse[MCPServerTestResponse])
async def test_mcp_server(
    serverId: str,
    db: DBSession,
    current_user: TenantAdmin,
):
    """Test MCP server connection."""
    result = await db.execute(select(MCPServer).where(MCPServer.id == serverId))
    server = result.scalar_one_or_none()
    
    if not server:
        raise HTTPException(status_code=404, detail="MCP服务器不存在")
    
    start_time = time.time()
    
    try:
        if server.transport_type == "stdio":
            # Test stdio transport by running the command
            success, message = await _test_stdio_server(server)
            latency_ms = int((time.time() - start_time) * 1000)
            
            server.last_check_at = datetime.utcnow()
            server.last_check_status = "success" if success else "failed"
            await db.commit()
            
            return BaseResponse(
                data=MCPServerTestResponse(success=success, message=message, latencyMs=latency_ms)
            )
        else:
            # Test HTTP/SSE transport
            async with httpx.AsyncClient(timeout=server.timeout_seconds) as client:
                response = await client.get(f"{server.base_url}/health")
                latency_ms = int((time.time() - start_time) * 1000)
                
                if response.status_code == 200:
                    server.last_check_at = datetime.utcnow()
                    server.last_check_status = "success"
                    await db.commit()
                    
                    return BaseResponse(
                        data=MCPServerTestResponse(success=True, message="连接成功", latencyMs=latency_ms)
                    )
                else:
                    server.last_check_at = datetime.utcnow()
                    server.last_check_status = "failed"
                    await db.commit()
                    
                    return BaseResponse(
                        data=MCPServerTestResponse(success=False, message=f"HTTP {response.status_code}", latencyMs=latency_ms)
                    )
    except Exception as e:
        latency_ms = int((time.time() - start_time) * 1000)
        server.last_check_at = datetime.utcnow()
        server.last_check_status = "failed"
        await db.commit()
        
        return BaseResponse(
            data=MCPServerTestResponse(success=False, message=str(e), latencyMs=latency_ms)
        )


async def _test_stdio_server(server: MCPServer) -> tuple[bool, str]:
    """Test stdio MCP server by initializing connection."""
    try:
        process = await asyncio.create_subprocess_exec(
            server.command,
            *server.args if server.args else [],
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=server.env if server.env else None,
        )
        
        # Send initialize request
        init_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "test", "version": "1.0"}
            }
        }
        
        process.stdin.write((json.dumps(init_request) + "\n").encode())
        await process.stdin.drain()
        
        # Read response with timeout
        try:
            response_line = await asyncio.wait_for(
                process.stdout.readline(),
                timeout=server.timeout_seconds
            )
            response = json.loads(response_line.decode().strip())
            
            if "result" in response:
                # Send initialized notification
                initialized_notification = {
                    "jsonrpc": "2.0",
                    "method": "notifications/initialized",
                }
                process.stdin.write((json.dumps(initialized_notification) + "\n").encode())
                await process.stdin.drain()
                
                process.terminate()
                await process.wait()
                return True, "连接成功"
            else:
                process.terminate()
                await process.wait()
                return False, response.get("error", {}).get("message", "初始化失败")
                
        except asyncio.TimeoutError:
            process.terminate()
            await process.wait()
            return False, "连接超时"
            
    except Exception as e:
        return False, str(e)


@router.patch("/servers/{serverId}/status", response_model=BaseResponse[MCPServerResponse])
async def update_mcp_server_status(
    serverId: str,
    request: MCPServerStatusUpdate,
    db: DBSession,
    current_user: TenantAdmin,
):
    """Update MCP server status."""
    result = await db.execute(select(MCPServer).where(MCPServer.id == serverId))
    server = result.scalar_one_or_none()
    
    if not server:
        raise HTTPException(status_code=404, detail="MCP服务器不存在")
    
    server.status = request.status
    await db.commit()
    await db.refresh(server)
    
    # Get tool count
    tool_count_result = await db.execute(
        select(func.count()).select_from(MCPTool).where(MCPTool.server_id == server.id)
    )
    tool_count = tool_count_result.scalar() or 0
    
    return BaseResponse(
        data=MCPServerResponse(
            serverId=server.id,
            name=server.name,
            transportType=server.transport_type,
            command=server.command,
            args=server.args,
            env=server.env,
            baseUrl=server.base_url,
            authType=server.auth_type,
            status=server.status,
            timeoutSeconds=server.timeout_seconds,
            description=server.description,
            lastCheckAt=server.last_check_at,
            lastCheckStatus=server.last_check_status,
            toolCount=tool_count,
            createdAt=server.created_at,
            updatedAt=server.updated_at,
        )
    )


@router.post("/servers/{serverId}/discover-tools", response_model=BaseResponse[MCPToolDiscoverResponse])
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
    
    try:
        if server.transport_type == "stdio":
            # Discover tools via stdio
            tools_data = await _discover_stdio_tools(server)
        else:
            # Discover tools via HTTP/SSE
            tools_data = await _discover_http_tools(server)
        
        # Save discovered tools to database
        discovered = []
        for tool_info in tools_data:
            tool_code = tool_info.get("name", "")
            
            # Check if tool already exists
            existing = await db.execute(
                select(MCPTool).where(
                    MCPTool.server_id == serverId,
                    MCPTool.tool_code == tool_code,
                )
            )
            if existing.scalar_one_or_none():
                continue
            
            # Create MCP tool
            mcp_tool = MCPTool(
                id=generate_id(),
                server_id=serverId,
                tool_code=tool_code,
                tool_name=tool_info.get("name", ""),
                description=tool_info.get("description", ""),
                schema=tool_info.get("inputSchema", {}),
                status="enabled",
            )
            db.add(mcp_tool)
            
            # Also create ToolDefinition for unified tool management
            tool_def = ToolDefinition(
                id=generate_id(),
                code=tool_code,
                name=tool_info.get("name", ""),
                type="mcp_tool",
                description=tool_info.get("description", ""),
                config={
                    "server_id": serverId,
                    "transport_type": server.transport_type,
                    "command": server.command,
                    "args": server.args,
                    "env": server.env,
                    "base_url": server.base_url,
                    "auth_type": server.auth_type,
                    "auth_config": server.auth_config,
                    "input_schema": tool_info.get("inputSchema", {}),
                },
                status="enabled",
                health_status="healthy",
            )
            db.add(tool_def)
            
            # Auto-bind to default tenant
            from app.models.tool import TenantToolPermission
            permission = TenantToolPermission(
                id=generate_id(),
                tenant_id="default",
                tool_id=tool_def.id,
                enabled=True,
            )
            db.add(permission)
            
            discovered.append({
                "toolCode": tool_code,
                "name": tool_info.get("name", ""),
                "description": tool_info.get("description", ""),
            })
        
        await db.commit()
        
        return BaseResponse(
            data=MCPToolDiscoverResponse(toolList=discovered),
            message=f"发现 {len(discovered)} 个MCP工具"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"发现工具失败: {str(e)}")


async def _discover_stdio_tools(server: MCPServer) -> list[dict]:
    """Discover tools from stdio MCP server."""
    
    process = await asyncio.create_subprocess_exec(
        server.command,
        *server.args if server.args else [],
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env=server.env if server.env else None,
    )
    
    try:
        # 1. Initialize
        init_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "discover", "version": "1.0"}
            }
        }
        
        process.stdin.write((json.dumps(init_request) + "\n").encode())
        await process.stdin.drain()
        
        # Read initialize response (skip non-JSON lines)
        response = None
        while True:
            try:
                line = await asyncio.wait_for(
                    process.stdout.readline(),
                    timeout=server.timeout_seconds
                )
                if not line:
                    break
                line_str = line.decode().strip()
                if not line_str:
                    continue
                print(f"[MCP] 收到行: {line_str[:200]}")
                try:
                    data = json.loads(line_str)
                    if "jsonrpc" in data:
                        response = data
                        break
                except json.JSONDecodeError:
                    continue
            except asyncio.TimeoutError:
                break
        
        if not response:
            process.terminate()
            await process.wait()
            raise Exception("初始化超时")
        
        if "error" in response:
            process.terminate()
            await process.wait()
            raise Exception(response["error"].get("message", "初始化失败"))
        
        print(f"[MCP] 初始化成功: {response.get('result', {}).get('serverInfo', {})}")
        
        # 2. Send initialized notification
        initialized_notification = {
            "jsonrpc": "2.0",
            "method": "notifications/initialized",
        }
        process.stdin.write((json.dumps(initialized_notification) + "\n").encode())
        await process.stdin.drain()
        
        # 3. List tools
        list_tools_request = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list",
            "params": {}
        }
        
        process.stdin.write((json.dumps(list_tools_request) + "\n").encode())
        await process.stdin.drain()
        
        # Read tools response (skip non-JSON lines)
        response = None
        while True:
            try:
                line = await asyncio.wait_for(
                    process.stdout.readline(),
                    timeout=server.timeout_seconds
                )
                if not line:
                    break
                line_str = line.decode().strip()
                if not line_str:
                    continue
                print(f"[MCP] 收到行: {line_str[:200]}")
                try:
                    data = json.loads(line_str)
                    if "jsonrpc" in data:
                        response = data
                        break
                except json.JSONDecodeError:
                    continue
            except asyncio.TimeoutError:
                break
        
        process.terminate()
        await process.wait()
        
        if not response:
            raise Exception("获取工具列表超时")
        
        if "result" in response:
            tools = response["result"].get("tools", [])
            print(f"[MCP] 发现 {len(tools)} 个工具")
            return tools
        else:
            raise Exception(response.get("error", {}).get("message", "获取工具列表失败"))
            
    except asyncio.TimeoutError:
        process.terminate()
        await process.wait()
        raise Exception("连接超时")
    except json.JSONDecodeError as e:
        process.terminate()
        await process.wait()
        raise Exception(f"解析响应失败: {str(e)}")


async def _discover_http_tools(server: MCPServer) -> list[dict]:
    """Discover tools from HTTP/SSE MCP server."""
    async with httpx.AsyncClient(timeout=server.timeout_seconds) as client:
        # Build auth headers
        headers = {}
        if server.auth_type == "bearer" and server.auth_config:
            headers["Authorization"] = f"Bearer {server.auth_config.get('token', '')}"
        elif server.auth_type == "api_key" and server.auth_config:
            headers["X-API-Key"] = server.auth_config.get("api_key", "")
        
        response = await client.post(
            f"{server.base_url}/tools/list",
            json={},
            headers=headers,
        )
        
        if response.status_code != 200:
            raise Exception(f"MCP服务器返回错误: HTTP {response.status_code}")
        
        return response.json().get("tools", [])


# ============ MCP Tools ============


@router.get("/tools", response_model=BaseResponse[PaginatedResponse[MCPToolResponse]])
async def list_mcp_tools(
    db: DBSession,
    current_user: TenantAdmin,
    pageNum: int = Query(1, ge=1),
    pageSize: int = Query(20, ge=1),
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
            name=t.tool_name,
            description=t.description,
            inputSchema=t.schema,
            enabled=t.status == "enabled",
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
    request: MCPToolBindTenantsRequest,
    db: DBSession,
    current_user: TenantAdmin,
):
    """Bind MCP tool to tenants."""
    from app.models.tool import TenantToolPermission
    
    # Get MCP tool
    result = await db.execute(select(MCPTool).where(MCPTool.id == toolId))
    mcp_tool = result.scalar_one_or_none()
    
    if not mcp_tool:
        raise HTTPException(status_code=404, detail="MCP工具不存在")
    
    # Get corresponding ToolDefinition
    tool_def_result = await db.execute(
        select(ToolDefinition).where(ToolDefinition.code == mcp_tool.tool_code)
    )
    tool_def = tool_def_result.scalar_one_or_none()
    
    if not tool_def:
        raise HTTPException(status_code=404, detail="工具定义不存在")
    
    bound_count = 0
    for tenant_id in request.tenant_ids:
        # Verify tenant exists
        tenant = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
        if not tenant.scalar_one_or_none():
            continue
        
        # Check if permission already exists
        existing = await db.execute(
            select(TenantToolPermission).where(
                TenantToolPermission.tenant_id == tenant_id,
                TenantToolPermission.tool_id == tool_def.id,
            )
        )
        if existing.scalar_one_or_none():
            continue
        
        # Create permission
        permission = TenantToolPermission(
            id=generate_id(),
            tenant_id=tenant_id,
            tool_id=tool_def.id,
            enabled=True,
        )
        db.add(permission)
        bound_count += 1
    
    await db.commit()
    
    return BaseResponse(message=f"成功绑定 {bound_count} 个租户")