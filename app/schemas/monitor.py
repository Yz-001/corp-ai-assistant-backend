"""Monitor schemas."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class OnlineUsersResponse(BaseModel):
    """Online users response."""

    online_users: int = Field(alias="onlineUsers", description="Current online users count")
    active_users: int = Field(alias="activeUsers", description="Active users in last 30 min")

    model_config = {"populate_by_name": True}


class TrafficResponse(BaseModel):
    """Traffic response for a time point."""

    time: str = Field(description="Time point (e.g., '15:00')")
    requests: int = Field(description="Request count for this time point")

    model_config = {"populate_by_name": True}


class TokensResponse(BaseModel):
    """Tokens response for a time point."""

    time: str = Field(description="Time point (e.g., '15:00')")
    tokens: int = Field(description="Token count for this time point")

    model_config = {"populate_by_name": True}


class ErrorsResponse(BaseModel):
    """Errors response for a time point."""

    time: str = Field(description="Time point (e.g., '15:00')")
    errors: int = Field(description="Error count for this time point")

    model_config = {"populate_by_name": True}


class ResponseTimeResponse(BaseModel):
    """Response time response for a time point."""

    time: str = Field(description="Time point (e.g., '15:00')")
    avg_latency_ms: int = Field(alias="avgLatencyMs", description="Average latency in ms")

    model_config = {"populate_by_name": True}
