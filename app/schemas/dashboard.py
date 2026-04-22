"""Dashboard schemas."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class DashboardOverviewResponse(BaseModel):
    """Dashboard overview response."""

    online_users: int = Field(default=0, alias="onlineUsers", description="Current online users")
    today_active_users: int = Field(default=0, alias="todayActiveUsers", description="Today active users")
    today_qa_count: int = Field(default=0, alias="todayQaCount", description="Today QA count")
    today_request_count: int = Field(default=0, alias="todayRequestCount", description="Today request count")
    today_token_count: int = Field(default=0, alias="todayTokenCount", description="Today token count")
    today_upload_count: int = Field(default=0, alias="todayUploadCount", description="Today upload count")
    today_tool_calls: int = Field(default=0, alias="todayToolCalls", description="Today tool calls")
    error_rate: float = Field(default=0.0, alias="errorRate", description="Error rate")
    avg_latency_ms: int = Field(default=0, alias="avgLatencyMs", description="Average latency in ms")

    model_config = {"populate_by_name": True}


class TrendDataPoint(BaseModel):
    """Trend data point."""

    date: str = Field(description="Date or time label")
    value: int | float = Field(description="Value")

    model_config = {"populate_by_name": True}


class TrendResponse(BaseModel):
    """Trend response."""

    qa_trend: list[dict[str, Any]] = Field(default_factory=list, alias="qaTrend", description="QA trend")
    token_trend: list[dict[str, Any]] = Field(default_factory=list, alias="tokenTrend", description="Token trend")
    request_trend: list[dict[str, Any]] = Field(default_factory=list, alias="requestTrend", description="Request trend")
    error_trend: list[dict[str, Any]] = Field(default_factory=list, alias="errorTrend", description="Error trend")
    online_trend: list[dict[str, Any]] = Field(default_factory=list, alias="onlineTrend", description="Online trend")
    latency_trend: list[dict[str, Any]] = Field(default_factory=list, alias="latencyTrend", description="Latency trend")

    model_config = {"populate_by_name": True}


class RankingItem(BaseModel):
    """Ranking item."""

    id: str = Field(description="ID")
    name: str = Field(description="Name")
    value: int | float = Field(description="Value")
    rank: int = Field(description="Rank")

    model_config = {"populate_by_name": True}


class RankingResponse(BaseModel):
    """Ranking response."""

    tenant_ranking: list[dict[str, Any]] = Field(default_factory=list, alias="tenantRanking", description="Tenant ranking")
    user_ranking: list[dict[str, Any]] = Field(default_factory=list, alias="userRanking", description="User ranking")
    tool_ranking: list[dict[str, Any]] = Field(default_factory=list, alias="toolRanking", description="Tool ranking")
    hot_question_ranking: list[dict[str, Any]] = Field(
        default_factory=list, alias="hotQuestionRanking", description="Hot question ranking"
    )

    model_config = {"populate_by_name": True}