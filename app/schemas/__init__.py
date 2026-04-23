"""Schemas module initialization."""

from app.schemas.base import BaseResponse, PaginatedResponse, PaginationParams
from app.schemas.auth import (
    LoginRequest,
    LoginResponse,
    RefreshTokenRequest,
    TokenResponse,
    UserInfoResponse,
)
from app.schemas.chat import (
    SessionCreate,
    SessionUpdate,
    SessionResponse,
    SessionListResponse,
    SessionDetailResponse,
    MessageCreate,
    MessageResponse,
    StreamMessageEvent,
    PromptResponse,
    SuggestionResponse,
)
from app.schemas.document import (
    DocumentUploadResponse,
    DocumentResponse,
    DocumentListResponse,
    DocumentChunkResponse,
)
from app.schemas.tenant import (
    TenantCreate,
    TenantUpdate,
    TenantResponse,
    TenantListResponse,
    TenantUsageResponse,
)
from app.schemas.log import (
    QALogResponse,
    QALogListResponse,
    ToolLogResponse,
    AuditLogResponse,
)
from app.schemas.tool import (
    ToolCreate,
    ToolUpdate,
    ToolResponse,
    ToolListResponse,
    ToolStatsResponse,
)
from app.schemas.mcp import (
    MCPServerCreate,
    MCPServerUpdate,
    MCPServerResponse,
    MCPToolResponse,
)
from app.schemas.dashboard import (
    DashboardOverviewResponse,
    TrendResponse,
    RankingResponse,
)
from app.schemas.monitor import (
    OnlineUsersResponse,
    TrafficResponse,
    TokensResponse,
    ErrorsResponse,
    ResponseTimeResponse,
)

__all__ = [
    # Base
    "BaseResponse",
    "PaginatedResponse",
    "PaginationParams",
    # Auth
    "LoginRequest",
    "LoginResponse",
    "RefreshTokenRequest",
    "TokenResponse",
    "UserInfoResponse",
    # Chat
    "SessionCreate",
    "SessionUpdate",
    "SessionResponse",
    "SessionListResponse",
    "SessionDetailResponse",
    "MessageCreate",
    "MessageResponse",
    "StreamMessageEvent",
    "PromptResponse",
    "SuggestionResponse",
    # Document
    "DocumentUploadResponse",
    "DocumentResponse",
    "DocumentListResponse",
    "DocumentChunkResponse",
    # Tenant
    "TenantCreate",
    "TenantUpdate",
    "TenantResponse",
    "TenantListResponse",
    "TenantUsageResponse",
    # Log
    "QALogResponse",
    "QALogListResponse",
    "ToolLogResponse",
    "AuditLogResponse",
    # Tool
    "ToolCreate",
    "ToolUpdate",
    "ToolResponse",
    "ToolListResponse",
    "ToolStatsResponse",
    # MCP
    "MCPServerCreate",
    "MCPServerUpdate",
    "MCPServerResponse",
    "MCPToolResponse",
    # Dashboard
    "DashboardOverviewResponse",
    "TrendResponse",
    "RankingResponse",
    # Monitor
    "OnlineUsersResponse",
    "TrafficResponse",
    "TokensResponse",
    "ErrorsResponse",
    "ResponseTimeResponse",
]