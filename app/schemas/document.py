"""Document schemas."""

from datetime import datetime

from pydantic import BaseModel, Field


class DocumentUploadResponse(BaseModel):
    """Document upload response."""

    document_id: str = Field(alias="documentId", description="Document ID")
    status: str = Field(description="Document status")

    model_config = {"populate_by_name": True}


class DocumentResponse(BaseModel):
    """Document response."""

    document_id: str = Field(alias="documentId", description="Document ID")
    name: str = Field(description="Document name")
    file_name: str = Field(alias="fileName", description="File name")
    file_type: str = Field(alias="fileType", description="File type")
    file_size: int = Field(alias="fileSize", description="File size in bytes")
    tenant_id: str = Field(alias="tenantId", description="Tenant ID")
    tenant_name: str | None = Field(default=None, alias="tenantName", description="Tenant name")
    visibility: str = Field(description="Visibility: public, private")
    status: str = Field(description="Document status")
    chunk_count: int = Field(default=0, alias="chunkCount", description="Chunk count")
    created_by: str | None = Field(default=None, alias="createdBy", description="Created by user ID")
    error_message: str | None = Field(default=None, alias="errorMessage", description="Error message")
    created_at: datetime = Field(alias="createdAt", description="Created time")
    updated_at: datetime = Field(alias="updatedAt", description="Updated time")

    model_config = {"populate_by_name": True}


class DocumentListResponse(BaseModel):
    """Document list response."""

    document_id: str = Field(alias="documentId", description="Document ID")
    name: str = Field(description="Document name")
    file_name: str = Field(alias="fileName", description="File name")
    file_type: str = Field(alias="fileType", description="File type")
    file_size: int = Field(alias="fileSize", description="File size")
    tenant_name: str | None = Field(default=None, alias="tenantName", description="Tenant name")
    visibility: str = Field(description="Visibility")
    status: str = Field(description="Status")
    chunk_count: int = Field(default=0, alias="chunkCount", description="Chunk count")
    created_at: datetime = Field(alias="createdAt", description="Created time")

    model_config = {"populate_by_name": True}


class DocumentChunkResponse(BaseModel):
    """Document chunk response."""

    chunk_id: str = Field(alias="chunkId", description="Chunk ID")
    chunk_index: int = Field(alias="chunkIndex", description="Chunk index")
    content: str = Field(description="Chunk content")
    token_count: int = Field(default=0, alias="tokenCount", description="Token count")

    model_config = {"populate_by_name": True}