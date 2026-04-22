"""Base schemas for API responses."""

from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class BaseResponse(BaseModel, Generic[T]):
    """Standard API response format."""

    code: int = Field(default=0, description="Response code, 0 means success")
    message: str = Field(default="success", description="Response message")
    data: T | None = Field(default=None, description="Response data")


class PaginationParams(BaseModel):
    """Pagination parameters."""

    page_num: int = Field(default=1, ge=1, alias="pageNum", description="Page number")
    page_size: int = Field(default=20, ge=1, le=100, alias="pageSize", description="Page size")

    model_config = {"populate_by_name": True}


class PaginatedResponse(BaseModel, Generic[T]):
    """Paginated response data."""

    list: list[T] = Field(default_factory=list, description="Data list")
    total: int = Field(default=0, description="Total count")
    page_num: int = Field(default=1, alias="pageNum", description="Current page number")
    page_size: int = Field(default=20, alias="pageSize", description="Page size")

    model_config = {"populate_by_name": True}


class SourceReference(BaseModel):
    """Source reference for RAG answers."""

    document_id: str = Field(alias="documentId", description="Document ID")
    document_name: str = Field(alias="documentName", description="Document name")
    chunk_id: str = Field(alias="chunkId", description="Chunk ID")
    chunk_index: int = Field(alias="chunkIndex", description="Chunk index")
    snippet: str = Field(default="", description="Text snippet")
    score: float = Field(default=0.0, description="Relevance score")

    model_config = {"populate_by_name": True}


class TokenUsage(BaseModel):
    """Token usage information."""

    prompt_tokens: int = Field(alias="promptTokens", description="Prompt tokens")
    completion_tokens: int = Field(alias="completionTokens", description="Completion tokens")
    total_tokens: int = Field(alias="totalTokens", description="Total tokens")

    model_config = {"populate_by_name": True}


class ToolCallInfo(BaseModel):
    """Tool call information."""

    tool_id: str = Field(alias="toolId", description="Tool ID")
    tool_name: str = Field(alias="toolName", description="Tool name")
    arguments: dict[str, Any] = Field(default_factory=dict, description="Tool arguments")
    result: dict[str, Any] | None = Field(default=None, description="Tool result")

    model_config = {"populate_by_name": True}