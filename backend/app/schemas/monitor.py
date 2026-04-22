"""Monitor schemas."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class OnlineUsersResponse(BaseModel):
    """Online users response."""

    current_online_users: int = Field(alias="currentOnlineUsers", description="Current online users count")
    trend: list[dict[str, Any]] = Field(default_factory=list, description="Online users trend")

    model_config = {"populate_by_name": True}


class TrafficResponse(BaseModel):
    """Traffic response."""

    request_count: int = Field(alias="requestCount", description="Total request count")
    requests_per_minute: int = Field(alias="requestsPerMinute", description="Requests per minute")
    trend: list[dict[str, Any]] = Field(default_factory=list, description="Traffic trend")

    model_config = {"populate_by_name": True}


class TokensResponse(BaseModel):
    """Tokens response."""

    total_tokens: int = Field(alias="totalTokens", description="Total tokens")
    tokens_per_minute: float = Field(alias="tokensPerMinute", description="Tokens per minute")
    trend: list[dict[str, Any]] = Field(default_factory=list, description="Tokens trend")

    model_config = {"populate_by_name": True}


class ErrorsResponse(BaseModel):
    """Errors response."""

    error_count: int = Field(alias="errorCount", description="Error count")
    error_rate: float = Field(alias="errorRate", description="Error rate")
    trend: list[dict[str, Any]] = Field(default_factory=list, description="Errors trend")

    model_config = {"populate_by_name": True}


class ResponseTimeResponse(BaseModel):
    """Response time response."""

    avg_response_time_ms: int = Field(alias="avgResponseTimeMs", description="Average response time in ms")
    trend: list[dict[str, Any]] = Field(default_factory=list, description="Response time trend")

    model_config = {"populate_by_name": True}