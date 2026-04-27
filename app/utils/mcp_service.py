from __future__ import annotations

"""MCP (Model Context Protocol) service for tool discovery and execution."""

import json
import asyncio
import httpx
import os
from typing import Any
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.mcp import MCPServer, MCPTool
from app.models.tool import ToolDefinition, TenantToolPermission
from app.utils.id import generate_id


# MCP JSON-RPC request ID counter
_mcp_request_id = 0


def get_mcp_request_id() -> int:
    """Get next MCP request ID."""
    global _mcp_request_id
    _mcp_request_id += 1
    return _mcp_request_id


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
        return bool(self.config.get("command"))
    
    async def _connect_websocket(self) -> bool:
        """Connect via WebSocket."""
        return bool(self.endpoint)
    
    async def list_tools(self) -> list[dict[str, Any]]:
        """Discover available tools from MCP server."""
        if self.transport_type == "sse":
            return await self._list_tools_sse()
        elif self.transport_type == "stdio":
            return await self._list_tools_stdio()
        elif self.transport_type == "websocket":
            return await self._list_tools_websocket()
        return []
    
    async def _list_tools_sse(self) -> list[dict[str, Any]]:
        """List tools via SSE/HTTP."""
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(
                    f"{self.endpoint}/tools/list",
                    json={},
                    headers=self.config.get("headers", {}),
                )
                if response.status_code == 200:
                    return response.json().get("tools", [])
                return []
        except Exception as e:
            print(f"[MCP] Error listing tools: {e}")
            return []
    
    async def _list_tools_stdio(self) -> list[dict[str, Any]]:
        """List tools via stdio using JSON-RPC protocol."""
        command = self.config.get("command")
        args = self.config.get("args", [])
        env = self.config.get("env", {})
        
        if not command:
            print("[MCP] No command specified for stdio transport")
            return []
        
        process = None
        try:
            print(f"[MCP] Starting stdio process: {command} {' '.join(args)}")
            
            process_env = dict(os.environ)
            process_env.update(env)
            
            process = await asyncio.create_subprocess_exec(
                command,
                *args,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=process_env,
            )
            
            # Initialize
            init_request = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "corp-ai-assistant", "version": "1.0.0"}
                }
            }
            process.stdin.write((json.dumps(init_request) + "\n").encode())
            await process.stdin.drain()
            
            response_line = await asyncio.wait_for(process.stdout.readline(), timeout=10.0)
            print(f"[MCP] Init response: {response_line.decode().strip()}")
            
            # Send initialized notification
            notification = {"jsonrpc": "2.0", "method": "notifications/initialized"}
            process.stdin.write((json.dumps(notification) + "\n").encode())
            await process.stdin.drain()
            
            # List tools
            list_request = {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}
            process.stdin.write((json.dumps(list_request) + "\n").encode())
            await process.stdin.drain()
            
            tools_line = await asyncio.wait_for(process.stdout.readline(), timeout=10.0)
            tools_response = json.loads(tools_line.decode())
            tools = tools_response.get("result", {}).get("tools", [])
            
            print(f"[MCP] Found {len(tools)} tools")
            return tools
            
        except asyncio.TimeoutError:
            print("[MCP] Timeout waiting for response")
            return []
        except Exception as e:
            print(f"[MCP] Error listing tools: {e}")
            return []
        finally:
            if process:
                process.terminate()
                try:
                    await asyncio.wait_for(process.wait(), timeout=5.0)
                except:
                    process.kill()
    
    async def _list_tools_websocket(self) -> list[dict[str, Any]]:
        """List tools via WebSocket."""
        return []
    
    async def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Execute a tool on the MCP server."""
        if self.transport_type == "sse":
            return await self._call_tool_sse(tool_name, arguments)
        elif self.transport_type == "stdio":
            return await self._call_tool_stdio(tool_name, arguments)
        elif self.transport_type == "websocket":
            return await self._call_tool_websocket(tool_name, arguments)
        return {"success": False, "error": f"Unsupported transport: {self.transport_type}"}
    
    async def _call_tool_sse(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Call tool via SSE/HTTP."""
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                response = await client.post(
                    f"{self.endpoint}/tools/call",
                    json={"name": tool_name, "arguments": arguments},
                    headers=self.config.get("headers", {}),
                )
                if response.status_code == 200:
                    return {"success": True, "data": response.json()}
                return {"success": False, "error": f"HTTP {response.status_code}"}
        except httpx.TimeoutException:
            return {"success": False, "error": "Timeout"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _call_tool_stdio(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Call tool via stdio."""
        command = self.config.get("command")
        args = self.config.get("args", [])
        env = self.config.get("env", {})
        
        if not command:
            return {"success": False, "error": "No command specified"}
        
        process = None
        try:
            process_env = dict(os.environ)
            process_env.update(env)
            
            process = await asyncio.create_subprocess_exec(
                command, *args,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=process_env,
            )
            
            # Initialize
            init_request = {
                "jsonrpc": "2.0", "id": 1, "method": "initialize",
                "params": {"protocolVersion": "2024-11-05", "capabilities": {},
                           "clientInfo": {"name": "corp-ai-assistant", "version": "1.0.0"}}
            }
            process.stdin.write((json.dumps(init_request) + "\n").encode())
            await process.stdin.drain()
            await process.stdout.readline()
            
            # Initialized notification
            notification = {"jsonrpc": "2.0", "method": "notifications/initialized"}
            process.stdin.write((json.dumps(notification) + "\n").encode())
            await process.stdin.drain()
            
            # Call tool
            call_request = {
                "jsonrpc": "2.0", "id": 2, "method": "tools/call",
                "params": {"name": tool_name, "arguments": arguments}
            }
            process.stdin.write((json.dumps(call_request) + "\n").encode())
            await process.stdin.drain()
            
            result_line = await asyncio.wait_for(process.stdout.readline(), timeout=30.0)
            result = json.loads(result_line.decode())
            
            if "error" in result:
                return {"success": False, "error": result["error"]}
            return {"success": True, "data": result.get("result", {})}
            
        except asyncio.TimeoutError:
            return {"success": False, "error": "Timeout"}
        except Exception as e:
            return {"success": False, "error": str(e)}
        finally:
            if process:
                process.terminate()
                try:
                    await asyncio.wait_for(process.wait(), timeout=5.0)
                except:
                    process.kill()
    
    async def _call_tool_websocket(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Call tool via WebSocket."""
        return {"success": False, "error": "WebSocket not implemented"}


class MCPService:
    """Service for managing MCP servers and tools."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def register_server(
        self, name: str, transport_type: str, endpoint: str, config: dict[str, Any] | None = None
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
        
        return {"success": connected, "status": server.status, "healthStatus": server.health_status}
    
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
            existing = await self.db.execute(
                select(MCPTool).where(
                    MCPTool.server_id == server_id,
                    MCPTool.name == tool_info.get("name"),
                )
            )
            if existing.scalar_one_or_none():
                continue
            
            mcp_tool = MCPTool(
                id=generate_id(),
                server_id=server_id,
                name=tool_info.get("name", ""),
                description=tool_info.get("description", ""),
                input_schema=tool_info.get("inputSchema", {}),
                enabled=True,
            )
            self.db.add(mcp_tool)
            
            tool_def = ToolDefinition(
                id=generate_id(),
                code=f"mcp_{server.id[:8]}_{tool_info.get('name', '')}",
                name=tool_info.get("name", ""),
                type="mcp_tool",
                description=tool_info.get("description", ""),
                config={"server_id": server_id, "tool_name": tool_info.get("name", "")},
                status="enabled",
                health_status="healthy",
            )
            self.db.add(tool_def)
            
            discovered.append({
                "id": mcp_tool.id,
                "name": mcp_tool.name,
                "description": mcp_tool.description,
                "inputSchema": mcp_tool.input_schema,
            })
        
        server.tool_count = len(discovered)
        await self.db.commit()
        return discovered
    
    async def execute_tool(
        self, server_id: str, tool_name: str, arguments: dict[str, Any]
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
        self, server_id: str, tenant_id: str, tool_names: list[str] | None = None
    ) -> int:
        """Bind MCP server tools to a tenant."""
        query = select(MCPTool).where(MCPTool.server_id == server_id)
        if tool_names:
            query = query.where(MCPTool.name.in_(tool_names))
        
        result = await self.db.execute(query)
        tools = result.scalars().all()
        
        bound_count = 0
        for tool in tools:
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
            
            existing = await self.db.execute(
                select(TenantToolPermission).where(
                    TenantToolPermission.tenant_id == tenant_id,
                    TenantToolPermission.tool_id == tool_def.id,
                )
            )
            if existing.scalar_one_or_none():
                continue
            
            permission = TenantToolPermission(
                id=generate_id(), tenant_id=tenant_id, tool_id=tool_def.id, enabled=True
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