"""Public API endpoints for external access without authentication."""

import json
import asyncio
from typing import Annotated

from fastapi import APIRouter, Query, HTTPException, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.utils.chat_service import ChatService
from app.utils.response import BaseResponse

router = APIRouter()

# Default tenant ID for public access
DEFAULT_TENANT_ID = "default"

# Customer service contact
CUSTOMER_SERVICE_MESSAGE = "抱歉，这个问题我暂时无法回答，您可以联系我们的专员为您解答，客服热线：400-882-6688"


# ==================== Request/Response Models ====================

class PreciseAnswerRequest(BaseModel):
    """Precise answer request for bot/external platforms."""
    
    query: str = Field(..., description="问题内容", min_length=1)
    tenant_id: str | None = Field(default=None, alias="tenantId", description="租户ID")
    include_private: bool = Field(default=False, alias="includePrivate", description="是否包含私有库")
    
    model_config = {"populate_by_name": True}


class PublicChatRequest(BaseModel):
    """Public chat request."""
    
    query: str = Field(..., description="问题内容", min_length=1)
    tenant_id: str | None = Field(default=None, alias="tenantId", description="租户ID")
    session_id: str | None = Field(default=None, alias="sessionId", description="会话ID（用于多轮对话）")
    include_private: bool = Field(default=False, alias="includePrivate", description="是否包含私有库")
    
    model_config = {"populate_by_name": True}


# ==================== Precise Answer Endpoint ====================

@router.post("/precise")
async def precise_answer(
    request: PreciseAnswerRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    精准回答接口 - 用于机器人/第三方平台调用
    
    特点：
    - 流式输出，只返回精确答案
    - 默认只搜索公开知识库
    - 无结果时返回友好提示 + 客服电话
    
    参数：
    - query: 问题内容
    - tenantId: 租户ID（可选，默认为 'default'）
    - includePrivate: 是否包含私有库（默认 false）
    """
    tenant_id = request.tenant_id or DEFAULT_TENANT_ID
    chat_service = ChatService(db, tenant_id)
    
    async def generate_stream():
        """Generate streaming response."""
        async for event_data in chat_service.generate_precise_answer(
            query=request.query,
            include_private=request.include_private,
        ):
            yield f"data: {json.dumps(event_data)}\n\n"
    
    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


# ==================== Public Chat Endpoint ====================

@router.post("/chat")
async def public_chat(
    request: PublicChatRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    公开聊天接口 - 用于嵌入其他平台的聊天功能
    
    特点：
    - 流式输出，完整的聊天体验
    - 支持多轮对话（通过 sessionId）
    - 默认只搜索公开知识库
    - 复用系统内部聊天逻辑
    
    参数：
    - query: 问题内容
    - tenantId: 租户ID（可选，默认为 'default'）
    - sessionId: 会话ID（可选，用于多轮对话）
    - includePrivate: 是否包含私有库（默认 false）
    """
    tenant_id = request.tenant_id or DEFAULT_TENANT_ID
    chat_service = ChatService(db, tenant_id)
    
    async def generate_stream():
        """Generate streaming response."""
        async for event_data in chat_service.generate_chat_answer(
            query=request.query,
            session_id=request.session_id,
            include_private=request.include_private,
        ):
            yield f"data: {json.dumps(event_data)}\n\n"
    
    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


# ==================== Legacy Search Endpoint (kept for compatibility) ====================

class PublicSearchRequest(BaseModel):
    """Public search request."""

    query: str = Field(..., description="Search query", min_length=1)
    tenant_id: str | None = Field(default=None, alias="tenantId", description="Optional tenant ID to limit search scope")
    top_k: int = Field(default=5, ge=1, le=20, description="Number of results to return")

    model_config = {"populate_by_name": True}


class PublicSearchResult(BaseModel):
    """Public search result item."""

    chunk_id: str = Field(alias="chunkId", description="Chunk ID")
    document_id: str = Field(alias="documentId", description="Document ID")
    document_name: str = Field(alias="documentName", description="Document name")
    chunk_index: int = Field(alias="chunkIndex", description="Chunk index")
    content: str = Field(description="Chunk content")
    score: float = Field(default=0, description="Relevance score")
    tenant_id: str = Field(alias="tenantId", description="Tenant ID")

    model_config = {"populate_by_name": True}


class PublicSearchResponse(BaseModel):
    """Public search response."""

    answer: str = Field(default="", description="AI generated answer from knowledge base")
    results: list[PublicSearchResult] = Field(default_factory=list, description="Search results")
    total: int = Field(default=0, description="Total number of results")
    query: str = Field(description="Original query")

    model_config = {"populate_by_name": True}


@router.post("/search", response_model=BaseResponse[PublicSearchResponse])
async def public_search(
    request: PublicSearchRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Search public knowledge base without authentication (Legacy).
    
    推荐使用 /precise 或 /chat 接口获得更好的体验。
    """
    from app.models.document import Document, DocumentChunk
    from app.utils.rag_service import RAGService
    
    tenant_id = request.tenant_id or DEFAULT_TENANT_ID
    
    # Search using RAG service with public visibility
    rag_service = RAGService(db, tenant_id)
    context, sources = await rag_service.build_context(
        request.query,
        visibility="public",
        max_chunks=request.top_k,
    )
    
    # If no results, return friendly message
    if not sources:
        return BaseResponse(
            data=PublicSearchResponse(
                answer="",
                results=[],
                total=0,
                query=request.query,
            ),
            message=CUSTOMER_SERVICE_MESSAGE,
        )
    
    # Generate answer using AI
    answer = ""
    try:
        from app.core.config import settings
        from openai import AsyncOpenAI
        
        if settings.openai_api_key:
            client = AsyncOpenAI(
                api_key=settings.openai_api_key,
                base_url=settings.openai_base_url,
            )
            
            prompt = f"""请根据以下参考资料回答用户的问题。要求回答简洁准确，直接提取关键信息回答。

参考资料：
{context}

用户问题：{request.query}

请直接回答："""
            
            response = await client.chat.completions.create(
                model=settings.llm_model_name,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=500,
                temperature=0.7,
            )
            answer = response.choices[0].message.content or ""
    except Exception as e:
        print(f"[Public Search] Error generating answer: {e}")
    
    # Build results
    results = [
        PublicSearchResult(
            chunk_id=s.get("chunkId", ""),
            document_id=s.get("documentId", ""),
            document_name=s.get("documentName", "Unknown"),
            chunk_index=s.get("chunkIndex", 0),
            content=s.get("content", ""),
            score=0.8,
            tenant_id=tenant_id,
        )
        for s in sources
    ]
    
    return BaseResponse(
        data=PublicSearchResponse(
            answer=answer,
            results=results,
            total=len(results),
            query=request.query,
        ),
    )