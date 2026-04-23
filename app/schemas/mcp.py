"""MCP schemas."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class MCPServerCreate(BaseModel):
    """Create MCP server request."""

    name: str = Field(min_length=1, max_length=100, description="Server name")
    base_url: str = Field(alias="baseUrl", description="Server base URL")
    auth_type: str = Field(default="none", alias="authType", description="Auth type: none, bearer, basic, api_key")
    auth_config: dict[str, Any] | None = Field(default=None, alias="authConfig", description="Auth configuration")
    timeout_seconds: int = Field(default=20, alias="timeoutSeconds", description="Timeout in seconds")
    description: str | None = Field(default=None, description="Server description")

    model_config = {"populate_by_name": True}


class MCPServerUpdate(BaseModel):
    """Update MCP server request."""

    name: str | None = Field(default=None, max_length=100, description="Server name")
    base_url: str | None = Field(default=None, alias="baseUrl", description="Server base URL")
    auth_type: str | None = Field(default=None, alias="authType", description="Auth type")
    auth_config: dict[str, Any] | None = Field(default=None, alias="authConfig", description="Auth configuration")
    timeout_seconds: int | None = Field(default=None, alias="timeoutSeconds", description="Timeout")
    description: str | None = Field(default=None, description="Server description")

    model_config = {"populate_by_name": True}


class MCPServerResponse(BaseModel):
    """MCP server response."""

    server_id: str = Field(alias="serverId", description="Server ID")
    name: str = Field(description="Server name")
    base_url: str = Field(alias="baseUrl", description="Server base URL")
    auth_type: str = Field(alias="authType", description="Auth type")
    status: str = Field(description="Status: enabled, disabled")
    timeout_seconds: int = Field(alias="timeoutSeconds", description="Timeout")
    description: str | None = Field(default=None, description="Server description")
    last_check_at: datetime | None = Field(default=None, alias="lastCheckAt", description="Last check time")
    last_check_status: str = Field(alias="lastCheckStatus", description="Last check status")
    tool_count: int = Field(default=0, alias="toolCount", description="Tool count")
    created_at: datetime = Field(alias="createdAt", description="Created time")
    updated_at: datetime = Field(alias="updatedAt", description="Updated time")

    model_config = {"populate_by_name": True}


class MCPServerTestResponse(BaseModel):
    """MCP server test response."""

    success: bool = Field(description="Whether test succeeded")
    message: str = Field(description="Test message")
    latency_ms: int = Field(default=0, alias="latencyMs", description="Latency in ms")

    model_config = {"populate_by_name": True}


class MCPToolResponse(BaseModel):
    """MCP tool response."""

    tool_id: str = Field(alias="toolId", description="Tool ID")
    server_id: str = Field(alias="serverId", description="Server ID")
    name: str = Field(description="Tool name")
    description: str | None = Field(default=None, description="Tool description")
    input_schema: dict[str, Any] | None = Field(default=None, alias="inputSchema", description="Tool input schema")
    enabled: bool = Field(default=True, description="Whether tool is enabled")
    created_at: datetime | None = Field(default=None, alias="createdAt", description="Created time")

    model_config = {"populate_by_name": True}


class MCPToolDiscoverResponse(BaseModel):
    """MCP tool discover response."""

    tool_list: list[dict[str, Any]] = Field(default_factory=list, alias="toolList", description="Discovered tools")

    model_config = {"populate_by_name": True}


class MCPToolBindTenantsRequest(BaseModel):
    """Bind tenants to MCP tool request."""

    tenant_ids: list[str] = Field(alias="tenantIds", description="Tenant IDs to bind")

    model_config = {"populate_by_name": True}


class MCPServerStatusUpdate(BaseModel):
    """Update MCP server status request."""

    status: str = Field(description="Status: enabled, disabled")