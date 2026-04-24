from __future__ import annotations

"""Tool execution schemas."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ToolExecuteRequest(BaseModel):
    """Tool execution request."""

    tool_id: str | None = Field(default=None, alias="toolId", description="Tool ID")
    tool_code: str | None = Field(default=None, alias="toolCode", description="Tool code")
    arguments: dict[str, Any] = Field(default_factory=dict, description="Tool arguments")
    session_id: str | None = Field(default=None, alias="sessionId", description="Chat session ID")
    message_id: str | None = Field(default=None, alias="messageId", description="Chat message ID")

    model_config = {"populate_by_name": True}


class ToolExecuteResponse(BaseModel):
    """Tool execution response."""

    success: bool = Field(description="Execution success")
    data: Any | None = Field(default=None, description="Execution result data")
    error: str | None = Field(default=None, description="Error message if failed")
    latency_ms: int | None = Field(default=None, alias="latencyMs", description="Execution latency in milliseconds")

    model_config = {"populate_by_name": True}


class ToolPermissionCreate(BaseModel):
    """Tool permission create request."""

    tenant_id: str = Field(alias="tenantId", description="Tenant ID")
    tool_id: str = Field(alias="toolId", description="Tool ID")
    enabled: bool = Field(default=True, description="Whether enabled")
    config: dict[str, Any] | None = Field(default=None, description="Tenant-specific config")

    model_config = {"populate_by_name": True}


class ToolPermissionResponse(BaseModel):
    """Tool permission response."""

    id: str = Field(description="Permission ID")
    tenant_id: str = Field(alias="tenantId", description="Tenant ID")
    tool_id: str = Field(alias="toolId", description="Tool ID")
    tool_name: str = Field(alias="toolName", description="Tool name")
    enabled: bool = Field(description="Whether enabled")
    config: dict[str, Any] | None = Field(default=None, description="Tenant-specific config")
    created_at: datetime = Field(alias="createdAt", description="Creation time")

    model_config = {"populate_by_name": True}