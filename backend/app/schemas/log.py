"""Log schemas."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.schemas.base import SourceReference


class QALogResponse(BaseModel):
    """QA log response."""

    log_id: str = Field(alias="logId", description="Log ID")
    tenant_name: str | None = Field(default=None, alias="tenantName", description="Tenant name")
    user_name: str | None = Field(default=None, alias="userName", description="User name")
    query: str = Field(description="User query")
    answer: str | None = Field(default=None, description="Answer")
    model_name: str | None = Field(default=None, alias="modelName", description="Model name")
    latency_ms: int = Field(default=0, alias="latencyMs", description="Latency in ms")
    prompt_tokens: int = Field(default=0, alias="promptTokens", description="Prompt tokens")
    completion_tokens: int = Field(default=0, alias="completionTokens", description="Completion tokens")
    total_tokens: int = Field(default=0, alias="totalTokens", description="Total tokens")
    status: str = Field(description="Status: success, failed")
    created_at: datetime = Field(alias="createdAt", description="Created time")

    model_config = {"populate_by_name": True}


class QALogListResponse(BaseModel):
    """QA log list response."""

    log_id: str = Field(alias="logId", description="Log ID")
    tenant_name: str | None = Field(default=None, alias="tenantName", description="Tenant name")
    user_name: str | None = Field(default=None, alias="userName", description="User name")
    query: str = Field(description="User query (truncated)")
    answer: str | None = Field(default=None, description="Answer (truncated)")
    model_name: str | None = Field(default=None, alias="modelName", description="Model name")
    latency_ms: int = Field(default=0, alias="latencyMs", description="Latency")
    total_tokens: int = Field(default=0, alias="totalTokens", description="Total tokens")
    status: str = Field(description="Status")
    created_at: datetime = Field(alias="createdAt", description="Created time")

    model_config = {"populate_by_name": True}


class QALogDetailResponse(BaseModel):
    """QA log detail response."""

    log_id: str = Field(alias="logId", description="Log ID")
    query: str = Field(description="User query")
    answer: str | None = Field(default=None, description="Answer")
    sources: list[SourceReference] = Field(default_factory=list, description="Source references")
    tool_calls: list[dict[str, Any]] = Field(default_factory=list, alias="toolCalls", description="Tool calls")
    latency_ms: int = Field(default=0, alias="latencyMs", description="Latency")
    prompt_tokens: int = Field(default=0, alias="promptTokens", description="Prompt tokens")
    completion_tokens: int = Field(default=0, alias="completionTokens", description="Completion tokens")
    total_tokens: int = Field(default=0, alias="totalTokens", description="Total tokens")
    error_message: str | None = Field(default=None, alias="errorMessage", description="Error message")

    model_config = {"populate_by_name": True}


class ToolLogResponse(BaseModel):
    """Tool call log response."""

    log_id: str = Field(alias="logId", description="Log ID")
    tenant_name: str | None = Field(default=None, alias="tenantName", description="Tenant name")
    tool_name: str = Field(alias="toolName", description="Tool name")
    request: dict[str, Any] | None = Field(default=None, description="Request data")
    response: dict[str, Any] | None = Field(default=None, description="Response data")
    latency_ms: int = Field(default=0, alias="latencyMs", description="Latency")
    status: str = Field(description="Status")
    error_message: str | None = Field(default=None, alias="errorMessage", description="Error message")
    created_at: datetime = Field(alias="createdAt", description="Created time")

    model_config = {"populate_by_name": True}


class AuditLogResponse(BaseModel):
    """Audit log response."""

    log_id: str = Field(alias="logId", description="Log ID")
    tenant_name: str | None = Field(default=None, alias="tenantName", description="Tenant name")
    operator_name: str | None = Field(default=None, alias="operatorName", description="Operator name")
    module: str = Field(description="Module")
    action: str = Field(description="Action")
    target_type: str | None = Field(default=None, alias="targetType", description="Target type")
    target_id: str | None = Field(default=None, alias="targetId", description="Target ID")
    detail: dict[str, Any] | None = Field(default=None, description="Detail")
    ip_address: str | None = Field(default=None, alias="ipAddress", description="IP address")
    created_at: datetime = Field(alias="createdAt", description="Created time")

    model_config = {"populate_by_name": True}