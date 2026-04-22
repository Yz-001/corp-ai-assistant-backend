"""Tenant schemas."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class TenantCreate(BaseModel):
    """Create tenant request."""

    name: str = Field(min_length=1, max_length=100, description="Tenant name")
    code: str = Field(min_length=1, max_length=50, description="Tenant code")
    type: str = Field(default="enterprise", description="Tenant type: public, sales, partner, enterprise")
    plan_type: str = Field(default="basic", alias="planType", description="Plan type: basic, pro, enterprise")
    status: str = Field(default="enabled", description="Status: enabled, disabled")
    quota_config: dict[str, Any] | None = Field(
        default=None, alias="quotaConfig", description="Quota configuration"
    )

    model_config = {"populate_by_name": True}


class TenantUpdate(BaseModel):
    """Update tenant request."""

    name: str | None = Field(default=None, max_length=100, description="Tenant name")
    type: str | None = Field(default=None, description="Tenant type")
    plan_type: str | None = Field(default=None, alias="planType", description="Plan type")
    quota_config: dict[str, Any] | None = Field(
        default=None, alias="quotaConfig", description="Quota configuration"
    )

    model_config = {"populate_by_name": True}


class TenantResponse(BaseModel):
    """Tenant response."""

    tenant_id: str = Field(alias="tenantId", description="Tenant ID")
    name: str = Field(description="Tenant name")
    code: str = Field(description="Tenant code")
    type: str = Field(description="Tenant type")
    status: str = Field(description="Status")
    plan_type: str = Field(alias="planType", description="Plan type")
    quota_config: dict[str, Any] | None = Field(default=None, alias="quotaConfig", description="Quota config")
    created_at: datetime = Field(alias="createdAt", description="Created time")
    updated_at: datetime = Field(alias="updatedAt", description="Updated time")

    model_config = {"populate_by_name": True}


class TenantListResponse(BaseModel):
    """Tenant list response."""

    tenant_id: str = Field(alias="tenantId", description="Tenant ID")
    name: str = Field(description="Tenant name")
    code: str = Field(description="Tenant code")
    type: str = Field(description="Tenant type")
    status: str = Field(description="Status")
    plan_type: str = Field(alias="planType", description="Plan type")
    user_count: int = Field(default=0, alias="userCount", description="User count")
    document_count: int = Field(default=0, alias="documentCount", description="Document count")
    request_count: int = Field(default=0, alias="requestCount", description="Request count")
    token_count: int = Field(default=0, alias="tokenCount", description="Token count")
    created_at: datetime = Field(alias="createdAt", description="Created time")

    model_config = {"populate_by_name": True}


class TenantUsageResponse(BaseModel):
    """Tenant usage response."""

    request_count: int = Field(default=0, alias="requestCount", description="Request count")
    token_count: int = Field(default=0, alias="tokenCount", description="Token count")
    document_count: int = Field(default=0, alias="documentCount", description="Document count")
    tool_call_count: int = Field(default=0, alias="toolCallCount", description="Tool call count")
    active_user_count: int = Field(default=0, alias="activeUserCount", description="Active user count")
    trend_list: list[dict[str, Any]] = Field(default_factory=list, alias="trendList", description="Trend data")

    model_config = {"populate_by_name": True}


class TenantStatusUpdate(BaseModel):
    """Update tenant status request."""

    status: str = Field(description="Status: enabled, disabled")