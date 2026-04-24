from __future__ import annotations

"""MCP (Model Context Protocol) service for tool discovery and execution."""

import json
import asyncio
import httpx
from typing import Any
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.mcp import MCPServer, MCPTool
from app.models.tool import ToolDefinition, TenantToolPermission
from app.utils.id import generate_id


class MCPClient:
    """Client for communicating with MCP servers."""
    
    def __init__(self, server: MCPServer):
        self.server = server
        self.endpoint = server.endpoint
        self.transport_type = server.transport_type
        self.config = server.config or {}
    
    async def connect(self) -> bool:
        """Establish connection to MCP server."""
        if self.transport_type == "sse":
            return await self._connect_sse()
        elif self.transport_type == "stdio":
            return await self._connect_stdio()
        elif self.transport_type == "websocket":
            return await self._connect_websocket()
        else:
            return False
    
    async def _connect_sse(self) -> bool:
        """Connect via Server-Sent Events."""
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(f"{self.endpoint}/health")
                return response.status_code == 200
        except Exception as e:
            print(f"[MCP] SSE connection failed: {e}")
            return False
    
    async def _connect_stdio(self) -> bool:
        """Connect via stdio (local process)."""
        # stdio connection would spawn a local process
        # For now, return True if config has command
        return bool(self.config.get("command"))
    
    async def _connect_websocket(self) -> bool:
        """Connect via WebSocket."""
        # WebSocket connection would use websockets library
        # For now, return True if endpoint is set
        return bool(self.endpoint)
    
    async def list_tools(self) -> list[dict[str, Any]]:
        """Discover available tools from MCP server."""
        tools = []
        
        if self.transport_type == "sse":
            tools = await self._list_tools_sse()
        elif self.transport_type == "stdio":
            tools = await self._list_tools_stdio()
        elif self.transport_type == "websocket":
            tools = await self._list_tools_websocket()
        
        return tools
    
    async def _list_tools_sse(self) -> list[dict[str, Any]]:
        """List tools via SSE/HTTP."""
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                # MCP protocol: tools/list endpoint
                response = await client.post(
                    f"{self.endpoint}/tools/list",
                    json={},
                    headers=self.config.get("headers", {}),
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return data.get("tools", [])
                else:
                    print(f"[MCP] Failed to list tools: {response.status_code}")
                    return []
        except Exception as e:
            print(f"[MCP] Error listing tools: {e}")
            return []
    
    async def _list_tools_stdio(self) -> list[dict[str, Any]]:
        """List tools via stdio."""
        # Would implement JSON-RPC over stdio
        # For now, return empty list
        return []
    
    async def _list_tools_websocket(self) -> list[dict[str, Any]]:
        """List tools via WebSocket."""
        # Would implement JSON-RPC over WebSocket
        # For now, return empty list
        return []
    
    async def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Execute a tool on the MCP server."""
        if self.transport_type == "sse":
            return await self._call_tool_sse(tool_name, arguments)
        elif self.transport_type == "stdio":
            return await self._call_tool_stdio(tool_name, arguments)
        elif self.transport_type == "websocket":
            return await self._call_tool_websocket(tool_name, arguments)
        else:
            return {"success": False, "error": f"Unsupported transport: {self.transport_type}"}
    
    async def _call_tool_sse(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Call tool via SSE/HTTP."""
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                response = await client.post(
                    f"{self.endpoint}/tools/call",
                    json={
                        "name": tool_name,
                        "arguments": arguments,
                    },
                    headers=self.config.get("headers", {}),
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return {"success": True, "data": data}
                else:
                    return {
                        "success": False,
                        "error": f"Tool call failed: {response.status_code}",
                        "body": response.text[:500] if response.text else None,
                    }
        except httpx.TimeoutException:
            return {"success": False, "error": "Tool call timeout"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _call_tool_stdio(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Call tool via stdio."""
        # Would implement JSON-RPC over stdio
        return {"success": False, "error": "stdio transport not implemented"}
    
    async def _call_tool_websocket(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Call tool via WebSocket."""
        # Would implement JSON-RPC over WebSocket
        return {"success": False, "error": "WebSocket transport not implemented"}


class MCPService:
    """Service for managing MCP servers and tools."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def register_server(
        self,
        name: str,
        transport_type: str,
        endpoint: str,
        config: dict[str, Any] | None = None,
    ) -> MCPServer:
        """Register a new MCP server."""
        server = MCPServer(
            id=generate_id(),
            name=name,
            transport_type=transport_type,
            endpoint=endpoint,
            config=config or {},
            status="inactive",
            health_status="unknown",
            tool_count=0,
        )
        self.db.add(server)
        await self.db.commit()
        await self.db.refresh(server)
        return server
    
    async def connect_server(self, server_id: str) -> dict[str, Any]:
        """Connect to an MCP server and update its status."""
        result = await self.db.execute(select(MCPServer).where(MCPServer.id == server_id))
        server = result.scalar_one_or_none()
        
        if not server:
            return {"success": False, "error": "服务器不存在"}
        
        client = MCPClient(server)
        connected = await client.connect()
        
        server.status = "active" if connected else "error"
        server.health_status = "healthy" if connected else "unhealthy"
        server.last_connected_at = datetime.utcnow() if connected else server.last_connected_at
        
        await self.db.commit()
        
        return {
            "success": connected,
            "status": server.status,
            "healthStatus": server.health_status,
        }
    
    async def discover_tools(self, server_id: str) -> list[dict[str, Any]]:
        """Discover tools from an MCP server and save to database."""
        result = await self.db.execute(select(MCPServer).where(MCPServer.id == server_id))
        server = result.scalar_one_or_none()
        
        if not server:
            return []
        
        client = MCPClient(server)
        tools = await client.list_tools()
        
        discovered = []
        for tool_info in tools:
            # Check if tool already exists
            existing = await self.db.execute(
                select(MCPTool).where(
                    MCPTool.server_id == server_id,
                    MCPTool.name == tool_info.get("name"),
                )
            )
            if existing.scalar_one_or_none():
                continue
            
            # Create MCP tool record
            mcp_tool = MCPTool(
                id=generate_id(),
                server_id=server_id,
                name=tool_info.get("name", ""),
                description=tool_info.get("description", ""),
                input_schema=tool_info.get("inputSchema", {}),
                enabled=True,
            )
            self.db.add(mcp_tool)
            
            # Also create a ToolDefinition for unified tool management
            tool_def = ToolDefinition(
                id=generate_id(),
                code=f"mcp_{server.code}_{tool_info.get('name', '')}",
                name=tool_info.get("name", ""),
                type="mcp_tool",
                description=tool_info.get("description", ""),
                config={
                    "server_id": server_id,
                    "tool_name": tool_info.get("name", ""),
                },
                status="active",
                health_status="healthy",
            )
            self.db.add(tool_def)
            
            discovered.append({
                "id": mcp_tool.id,
                "name": mcp_tool.name,
                "description": mcp_tool.description,
                "inputSchema": mcp_tool.input_schema,
            })
        
        # Update tool count
        server.tool_count = len(discovered)
        await self.db.commit()
        
        return discovered
    
    async def execute_tool(
        self,
        server_id: str,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute a tool on an MCP server."""
        result = await self.db.execute(select(MCPServer).where(MCPServer.id == server_id))
        server = result.scalar_one_or_none()
        
        if not server:
            return {"success": False, "error": "服务器不存在"}
        
        if server.status != "active":
            return {"success": False, "error": "服务器未连接"}
        
        client = MCPClient(server)
        return await client.call_tool(tool_name, arguments)
    
    async def bind_tools_to_tenant(
        self,
        server_id: str,
        tenant_id: str,
        tool_names: list[str] | None = None,
    ) -> int:
        """Bind MCP server tools to a tenant."""
        query = select(MCPTool).where(MCPTool.server_id == server_id)
        if tool_names:
            query = query.where(MCPTool.name.in_(tool_names))
        
        result = await self.db.execute(query)
        tools = result.scalars().all()
        
        bound_count = 0
        for tool in tools:
            # Get corresponding ToolDefinition
            tool_def_result = await self.db.execute(
                select(ToolDefinition).where(
                    ToolDefinition.type == "mcp_tool",
                    ToolDefinition.config["server_id"].as_string() == server_id,
                    ToolDefinition.config["tool_name"].as_string() == tool.name,
                )
            )
            tool_def = tool_def_result.scalar_one_or_none()
            
            if not tool_def:
                continue
            
            # Check if permission already exists
            existing = await self.db.execute(
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
            self.db.add(permission)
            bound_count += 1
        
        await self.db.commit()
        return bound_count
    
    async def get_server_health(self, server_id: str) -> dict[str, Any]:
        """Check health status of an MCP server."""
        result = await self.db.execute(select(MCPServer).where(MCPServer.id == server_id))
        server = result.scalar_one_or_none()
        
        if not server:
            return {"status": "unknown", "error": "服务器不存在"}
        
        client = MCPClient(server)
        connected = await client.connect()
        
        server.health_status = "healthy" if connected else "unhealthy"
        server.last_connected_at = datetime.utcnow() if connected else server.last_connected_at
        await self.db.commit()
        
        return {
            "serverId": server.id,
            "status": server.status,
            "healthStatus": server.health_status,
            "lastConnectedAt": server.last_connected_at,
        }
