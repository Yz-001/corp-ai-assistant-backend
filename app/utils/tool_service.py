from __future__ import annotations

"""Tool execution service."""

import time
import json
import httpx
from datetime import datetime
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tool import ToolDefinition, TenantToolPermission, ToolCallLog
from app.utils.id import generate_id


class ToolExecutor:
    """Tool execution engine for various tool types."""

    def __init__(self, db: AsyncSession, tenant_id: str):
        self.db = db
        self.tenant_id = tenant_id

    async def check_permission(self, tool_id: str) -> bool:
        """Check if tenant has permission to use the tool."""
        result = await self.db.execute(
            select(TenantToolPermission).where(
                TenantToolPermission.tenant_id == self.tenant_id,
                TenantToolPermission.tool_id == tool_id,
                TenantToolPermission.enabled == True,
            )
        )
        return result.scalar_one_or_none() is not None

    async def execute(
        self,
        tool_id: str,
        arguments: dict[str, Any],
        session_id: str | None = None,
        message_id: str | None = None,
    ) -> dict[str, Any]:
        """Execute a tool by ID with given arguments."""
        print("\n" + "=" * 60)
        print("[TOOL] 开始执行工具")
        print(f"[TOOL] Tool ID: {tool_id}")
        print(f"[TOOL] Arguments: {json.dumps(arguments, ensure_ascii=False)[:200]}")
        print(f"[TOOL] Tenant ID: {self.tenant_id}")
        print("=" * 60)
        
        start_time = time.time()
        
        # Get tool definition
        print("[TOOL] Step 1: 获取工具定义...")
        result = await self.db.execute(
            select(ToolDefinition).where(ToolDefinition.id == tool_id)
        )
        tool = result.scalar_one_or_none()
        
        if not tool:
            print("[TOOL] ❌ 工具不存在")
            return {"success": False, "error": "工具不存在"}
        
        print(f"[TOOL] ✅ 工具: {tool.name} (type: {tool.type}, status: {tool.status})")
        
        if tool.status != "enabled":
            print("[TOOL] ❌ 工具已禁用")
            return {"success": False, "error": "工具已禁用"}
        
        # Check permission
        print("[TOOL] Step 2: 检查租户权限...")
        has_permission = await self.check_permission(tool_id)
        if not has_permission:
            print("[TOOL] ❌ 租户无权使用该工具")
            return {"success": False, "error": "无权使用该工具"}
        print("[TOOL] ✅ 权限验证通过")
        
        # Execute based on tool type
        print(f"[TOOL] Step 3: 执行工具 (type: {tool.type})...")
        try:
            if tool.type == "internal_api":
                print("[TOOL]    调用内部API...")
                result_data = await self._execute_internal_api(tool, arguments)
            elif tool.type == "database_query":
                print("[TOOL]    执行数据库查询...")
                result_data = await self._execute_database_query(tool, arguments)
            elif tool.type == "http_service":
                print("[TOOL]    调用HTTP服务...")
                result_data = await self._execute_http_service(tool, arguments)
            elif tool.type == "mcp_tool":
                print("[TOOL]    调用MCP工具...")
                result_data = await self._execute_mcp_tool(tool, arguments)
            else:
                print(f"[TOOL] ❌ 未知工具类型: {tool.type}")
                result_data = {"success": False, "error": f"未知工具类型: {tool.type}"}
            
            status = "success" if result_data.get("success", True) else "failed"
            error_message = None if result_data.get("success", True) else result_data.get("error")
            
            if status == "success":
                print("[TOOL] ✅ 工具执行成功")
            else:
                print(f"[TOOL] ❌ 工具执行失败: {error_message}")
            
        except Exception as e:
            status = "failed"
            error_message = str(e)
            result_data = {"success": False, "error": str(e)}
            print(f"[TOOL] ❌ 执行异常: {str(e)}")
        
        # Log the call
        latency_ms = int((time.time() - start_time) * 1000)
        print(f"[TOOL] Step 4: 记录调用日志 (耗时: {latency_ms}ms)")
        await self._log_call(
            tool=tool,
            request=arguments,
            response=result_data,
            latency_ms=latency_ms,
            status=status,
            error_message=error_message,
            session_id=session_id,
            message_id=message_id,
        )
        
        print("=" * 60)
        print("[TOOL] ✅ 工具执行完成")
        print("=" * 60 + "\n")
        
        return result_data

    async def execute_by_code(
        self,
        tool_code: str,
        arguments: dict[str, Any],
        session_id: str | None = None,
        message_id: str | None = None,
    ) -> dict[str, Any]:
        """Execute a tool by code with given arguments."""
        result = await self.db.execute(
            select(ToolDefinition).where(ToolDefinition.code == tool_code)
        )
        tool = result.scalar_one_or_none()
        
        if not tool:
            return {"success": False, "error": "工具不存在"}
        
        return await self.execute(tool.id, arguments, session_id, message_id)

    async def _execute_internal_api(
        self, tool: ToolDefinition, arguments: dict[str, Any]
    ) -> dict[str, Any]:
        """Execute internal API tool."""
        config = tool.config or {}
        api_path = config.get("api_path")
        method = config.get("method", "GET").upper()
        
        if not api_path:
            return {"success": False, "error": "工具配置缺少api_path"}
        
        # Internal API calls would go through the app's internal router
        # For now, return a mock response
        return {
            "success": True,
            "data": {
                "message": f"Internal API {method} {api_path} called",
                "arguments": arguments,
            }
        }

    async def _execute_database_query(
        self, tool: ToolDefinition, arguments: dict[str, Any]
    ) -> dict[str, Any]:
        """Execute database query tool."""
        config = tool.config or {}
        query_template = config.get("query_template")
        
        if not query_template:
            return {"success": False, "error": "工具配置缺少query_template"}
        
        try:
            # Safely format query with arguments
            # Note: In production, use parameterized queries to prevent SQL injection
            query = query_template.format(**arguments)
            
            result = await self.db.execute(text(query))
            
            if result.returns_rows:
                rows = result.fetchall()
                columns = list(result.keys()) if hasattr(result, 'keys') else []
                data = [dict(zip(columns, row)) for row in rows]
                return {"success": True, "data": data, "count": len(data)}
            else:
                return {"success": True, "message": "查询执行成功", "rowcount": result.rowcount}
                
        except Exception as e:
            return {"success": False, "error": f"数据库查询失败: {str(e)}"}

    async def _execute_http_service(
        self, tool: ToolDefinition, arguments: dict[str, Any]
    ) -> dict[str, Any]:
        """Execute HTTP service tool."""
        config = tool.config or {}
        url = config.get("url")
        method = config.get("method", "POST").upper()
        headers = config.get("headers", {})
        timeout = config.get("timeout", 30)
        
        if not url:
            return {"success": False, "error": "工具配置缺少url"}
        
        # Replace URL parameters
        for key, value in arguments.items():
            url = url.replace("{" + key + "}", str(value))
        
        print(f"[TOOL]    请求URL: {url}")
        print(f"[TOOL]    Method: {method}")
        print(f"[TOOL]    Headers: {headers}")
        
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                if method == "GET":
                    response = await client.get(url, headers=headers)
                elif method == "POST":
                    response = await client.post(url, json=arguments, headers=headers)
                elif method == "PUT":
                    response = await client.put(url, json=arguments, headers=headers)
                elif method == "DELETE":
                    response = await client.delete(url, headers=headers)
                else:
                    return {"success": False, "error": f"不支持的HTTP方法: {method}"}
                
                if 200 <= response.status_code < 300:
                    try:
                        data = response.json()
                    except Exception:
                        data = response.text
                    return {"success": True, "data": data, "status_code": response.status_code}
                else:
                    return {
                        "success": False, 
                        "error": f"HTTP请求失败: {response.status_code}",
                        "status_code": response.status_code,
                        "body": response.text[:500] if response.text else None
                    }
        except httpx.TimeoutException:
            return {"success": False, "error": "请求超时"}
        except httpx.RequestError as e:
            return {"success": False, "error": f"请求失败: {str(e)}"}

    async def _execute_mcp_tool(
        self, tool: ToolDefinition, arguments: dict[str, Any]
    ) -> dict[str, Any]:
        """Execute MCP tool."""
        config = tool.config or {}
        server_id = config.get("server_id")
        tool_name = config.get("tool_name")
        
        if not server_id or not tool_name:
            return {"success": False, "error": "工具配置缺少server_id或tool_name"}
        
        # MCP tool execution would be handled by MCP service
        # For now, return a placeholder response
        return {
            "success": True,
            "data": {
                "message": f"MCP tool {tool_name} on server {server_id} called",
                "arguments": arguments,
            }
        }

    async def _log_call(
        self,
        tool: ToolDefinition,
        request: dict[str, Any],
        response: dict[str, Any],
        latency_ms: int,
        status: str,
        error_message: str | None = None,
        session_id: str | None = None,
        message_id: str | None = None,
    ):
        """Log tool call to database."""
        log = ToolCallLog(
            id=generate_id(),
            tenant_id=self.tenant_id,
            session_id=session_id,
            message_id=message_id,
            tool_id=tool.id,
            tool_name=tool.name,
            request=request,
            response=response,
            latency_ms=latency_ms,
            status=status,
            error_message=error_message,
        )
        self.db.add(log)
        await self.db.commit()

    async def get_available_tools(self) -> list[dict[str, Any]]:
        """Get all tools available to the current tenant."""
        print(f"[TOOL] get_available_tools - 查询租户可用工具")
        print(f"[TOOL]    tenant_id: {self.tenant_id}")
        
        # First check all permissions for this tenant
        all_perms = await self.db.execute(
            select(TenantToolPermission).where(
                TenantToolPermission.tenant_id == self.tenant_id
            )
        )
        perms = all_perms.scalars().all()
        print(f"[TOOL]    租户权限记录数: {len(perms)}")
        for p in perms:
            print(f"[TOOL]      - tool_id: {p.tool_id}, enabled: {p.enabled}")
        
        # Then check all tools
        all_tools = await self.db.execute(select(ToolDefinition))
        tools_all = all_tools.scalars().all()
        print(f"[TOOL]    系统工具总数: {len(tools_all)}")
        for t in tools_all:
            print(f"[TOOL]      - id: {t.id}, code: {t.code}, status: {t.status}")
        
        # Now do the join query
        result = await self.db.execute(
            select(ToolDefinition, TenantToolPermission)
            .join(TenantToolPermission, ToolDefinition.id == TenantToolPermission.tool_id)
            .where(
                TenantToolPermission.tenant_id == self.tenant_id,
                TenantToolPermission.enabled == True,
                ToolDefinition.status == "enabled",
            )
        )
        
        tools = []
        rows = result.all()
        print(f"[TOOL]    JOIN查询结果数: {len(rows)}")
        
        for tool, perm in rows:
            tools.append({
                "tool_id": tool.id,
                "code": tool.code,
                "name": tool.name,
                "type": tool.type,
                "description": tool.description,
                "config": perm.config or tool.config,
            })
        
        return tools
