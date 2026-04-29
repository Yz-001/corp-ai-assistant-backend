"""Chat schemas."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.schemas.base import SourceReference, TokenUsage, ToolCallInfo


class SessionCreate(BaseModel):
    """Create session request."""

    title: str = Field(default="新会话", max_length=200, description="Session title")
    channel: str = Field(default="web", description="Channel: web, public_widget, wecom")


class SessionUpdate(BaseModel):
    """Update session request."""

    title: str = Field(min_length=1, max_length=200, description="Session title")


class SessionResponse(BaseModel):
    """Session response."""

    session_id: str = Field(alias="sessionId", description="Session ID")
    title: str = Field(description="Session title")
    channel: str = Field(description="Channel")
    status: str = Field(description="Status")
    last_message_at: datetime | None = Field(
        default=None, alias="lastMessageAt", description="Last message time"
    )
    created_at: datetime = Field(alias="createdAt", description="Created time")
    updated_at: datetime = Field(alias="updatedAt", description="Updated time")

    model_config = {"populate_by_name": True}


class SessionListResponse(BaseModel):
    """Session list response."""

    session_id: str = Field(alias="sessionId", description="Session ID")
    title: str = Field(description="Session title")
    last_message_at: datetime | None = Field(
        default=None, alias="lastMessageAt", description="Last message time"
    )
    updated_at: datetime = Field(alias="updatedAt", description="Updated time")

    model_config = {"populate_by_name": True}


class MessageCreate(BaseModel):
    """Create message request."""

    session_id: str = Field(alias="sessionId", description="Session ID")
    query: str = Field(min_length=1, description="User query")
    channel: str = Field(default="web", description="Channel")

    model_config = {"populate_by_name": True}


class MessageResponse(BaseModel):
    """Message response."""

    message_id: str = Field(alias="messageId", description="Message ID")
    role: str = Field(description="Message role: user, assistant, system, tool")
    content: str = Field(description="Message content")
    status: str = Field(description="Message status")
    sources: list[SourceReference] = Field(default_factory=list, description="Source references")
    tool_calls: list[ToolCallInfo] = Field(default_factory=list, alias="toolCalls", description="Tool calls")
    token_usage: TokenUsage | None = Field(default=None, alias="tokenUsage", description="Token usage")
    created_at: datetime = Field(alias="createdAt", description="Created time")

    model_config = {"populate_by_name": True}


class StreamMessageEvent(BaseModel):
    """Stream message event for SSE."""

    event: str = Field(description="Event type: message_start, delta, tool_call, sources, message_end, error")
    data: dict[str, Any] = Field(default_factory=dict, description="Event data")


class PromptResponse(BaseModel):
    """Prompt tags response."""

    tags: list[str] = Field(default_factory=list, description="Prompt tags")


class SuggestionResponse(BaseModel):
    """Suggested questions response."""

    suggestions: list[str] = Field(default_factory=list, description="Suggested questions")


class ChatAnswerResponse(BaseModel):
    """Chat answer response."""

    message_id: str = Field(alias="messageId", description="Message ID")
    answer: str = Field(description="Answer content")
    sources: list[SourceReference] = Field(default_factory=list, description="Source references")
    tool_calls: list[ToolCallInfo] = Field(default_factory=list, alias="toolCalls", description="Tool calls")
    token_usage: TokenUsage | None = Field(default=None, alias="tokenUsage", description="Token usage")
    latency_ms: int = Field(default=0, alias="latencyMs", description="Latency in milliseconds")

    model_config = {"populate_by_name": True}


class SessionDetailResponse(BaseModel):
    """Session detail response with messages."""

    session_id: str = Field(alias="sessionId", description="Session ID")
    title: str = Field(description="Session title")
    channel: str = Field(description="Channel")
    status: str = Field(description="Status")
    last_message_at: datetime | None = Field(
        default=None, alias="lastMessageAt", description="Last message time"
    )
    created_at: datetime = Field(alias="createdAt", description="Created time")
    updated_at: datetime = Field(alias="updatedAt", description="Updated time")
    messages: list[MessageResponse] = Field(default_factory=list, description="Messages in session")

    model_config = {"populate_by_name": True}
