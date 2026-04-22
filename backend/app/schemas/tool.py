"""Tool schemas."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ToolCreate(BaseModel):
    """Create tool request."""

    code: str = Field(min_length=1, max_length=50, description="Tool code")
    name: str = Field(min_length=1, max_length=100, description="Tool name")
    type: str = Field(description="Tool type: internal_api, database_query, http_service, mcp_tool")
    description: str | None = Field(default=None, description="Tool description")
    config: dict[str, Any] | None = Field(default=None, description="Tool configuration")


class ToolUpdate(BaseModel):
    """Update tool request."""

    name: str | None = Field(default=None, max_length=100, description="Tool name")
    description: str | None = Field(default=None, description="Tool description")
    config: dict[str, Any] | None = Field(default=None, description="Tool configuration")


class ToolResponse(BaseModel):
    """Tool response."""

    tool_id: str = Field(alias="toolId", description="Tool ID")
    code: str = Field(description="Tool code")
    name: str = Field(description="Tool name")
    type: str = Field(description="Tool type")
    description: str | None = Field(default=None, description="Tool description")
    status: str = Field(description="Status: enabled, disabled")
    health_status: str = Field(alias="healthStatus", description="Health status")
    config: dict[str, Any] | None = Field(default=None, description="Tool configuration")
    created_at: datetime = Field(alias="createdAt", description="Created time")
    updated_at: datetime = Field(alias="updatedAt", description="Updated time")

    model_config = {"populate_by_name": True}


class ToolListResponse(BaseModel):
    """Tool list response."""

    tool_id: str = Field(alias="toolId", description="Tool ID")
    code: str = Field(description="Tool code")
    name: str = Field(description="Tool name")
    type: str = Field(description="Tool type")
    status: str = Field(description="Status")
    health_status: str = Field(alias="healthStatus", description="Health status")
    call_count: int = Field(default=0, alias="callCount", description="Call count")
    avg_latency_ms: int = Field(default=0, alias="avgLatencyMs", description="Average latency")
    error_rate: float = Field(default=0.0, alias="errorRate", description="Error rate")

    model_config = {"populate_by_name": True}


class ToolStatsResponse(BaseModel):
    """Tool statistics response."""

    tool_id: str = Field(alias="toolId", description="Tool ID")
    call_count: int = Field(default=0, alias="callCount", description="Total call count")
    success_count: int = Field(default=0, alias="successCount", description="Success count")
    error_count: int = Field(default=0, alias="errorCount", description="Error count")
    avg_latency_ms: int = Field(default=0, alias="avgLatencyMs", description="Average latency")
    trend: list[dict[str, Any]] = Field(default_factory=list, description="Trend data")

    model_config = {"populate_by_name": True}


class ToolStatusUpdate(BaseModel):
    """Update tool status request."""

    status: str = Field(description="Status: enabled, disabled")


class TenantToolPermissionUpdate(BaseModel):
    """Update tenant tool permission request."""

    enabled: bool = Field(description="Whether tool is enabled for tenant")
    config: dict[str, Any] | None = Field(default=None, description="Permission configuration")