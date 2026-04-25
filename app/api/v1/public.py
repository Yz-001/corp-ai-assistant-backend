"""Public API endpoints for knowledge base access without authentication."""

from typing import Annotated

from fastapi import APIRouter, Query, HTTPException, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.document import Document, DocumentChunk
from app.utils.rag_service import RAGService
from app.utils.response import BaseResponse

router = APIRouter()


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

    results: list[PublicSearchResult] = Field(default_factory=list, description="Search results")
    total: int = Field(default=0, description="Total number of results")
    query: str = Field(description="Original query")

    model_config = {"populate_by_name": True}


class PublicDocumentResponse(BaseModel):
    """Public document response."""

    document_id: str = Field(alias="documentId", description="Document ID")
    name: str = Field(description="Document name")
    file_type: str = Field(alias="fileType", description="File type")
    file_size: int = Field(alias="fileSize", description="File size")
    tenant_id: str = Field(alias="tenantId", description="Tenant ID")
    visibility: str = Field(description="Visibility")
    chunk_count: int = Field(default=0, alias="chunkCount", description="Chunk count")
    created_at: str = Field(alias="createdAt", description="Created time")

    model_config = {"populate_by_name": True}


class PublicDocumentListResponse(BaseModel):
    """Public document list response."""

    items: list[PublicDocumentResponse] = Field(default_factory=list, description="Document list")
    total: int = Field(default=0, description="Total count")
    page_num: int = Field(default=1, alias="pageNum", description="Page number")
    page_size: int = Field(default=20, alias="pageSize", description="Page size")

    model_config = {"populate_by_name": True}


async def get_public_documents(
    db: AsyncSession,
    tenant_id: str | None = None,
    page_num: int = 1,
    page_size: int = 20,
    keyword: str | None = None,
) -> tuple[list[Document], int]:
    """Get public documents, optionally filtered by tenant."""
    query = select(Document).where(
        Document.visibility == "public",
        Document.status == "completed",
    )
    
    if tenant_id:
        query = query.where(Document.tenant_id == tenant_id)
    
    if keyword:
        query = query.where(Document.name.ilike(f"%{keyword}%"))
    
    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # Get paginated results
    query = query.order_by(Document.created_at.desc())
    query = query.offset((page_num - 1) * page_size).limit(page_size)
    
    result = await db.execute(query)
    documents = result.scalars().all()
    
    return documents, total


@router.post("/search", response_model=BaseResponse[PublicSearchResponse])
async def public_search(
    request: PublicSearchRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Search public knowledge base without authentication.
    
    - If tenantId is provided, search only within that tenant's public documents
    - If tenantId is not provided, search across all public documents
    """
    # Get all public documents matching the tenant filter
    documents, _ = await get_public_documents(
        db, 
        tenant_id=request.tenant_id,
        page_num=1,
        page_size=100,  # Get more documents for broader search
    )
    
    print(f"[Public Search] Found {len(documents)} public documents")
    
    if not documents:
        return BaseResponse(
            data=PublicSearchResponse(
                results=[],
                total=0,
                query=request.query,
            ),
            message="No public documents found",
        )
    
    # Group documents by tenant for RAG search
    tenant_docs: dict[str, list[Document]] = {}
    for doc in documents:
        if doc.tenant_id not in tenant_docs:
            tenant_docs[doc.tenant_id] = []
        tenant_docs[doc.tenant_id].append(doc)
    
    all_results = []
    public_doc_ids = {d.id for d in documents}
    
    # Search in each tenant's collection
    for tenant_id, docs in tenant_docs.items():
        try:
            rag_service = RAGService(db, tenant_id)
            chunks = await rag_service.search_relevant_chunks(request.query, top_k=request.top_k)
            
            print(f"[Public Search] Tenant {tenant_id}: found {len(chunks)} chunks from RAG")
            
            # Filter to only include public documents
            for chunk in chunks:
                doc_id = chunk.get("document_id", "")
                if doc_id in public_doc_ids:
                    # Add tenant_id to chunk data
                    chunk["tenant_id"] = tenant_id
                    all_results.append(chunk)
                    print(f"[Public Search] Added chunk from doc: {doc_id}")
        except Exception as e:
            print(f"[Public Search] Error searching tenant {tenant_id}: {e}")
            import traceback
            traceback.print_exc()
            continue
    
    # If no results from RAG, fallback to direct database search on public docs
    if not all_results:
        print("[Public Search] No results from RAG, falling back to direct database search")
        try:
            # Get chunks from public documents directly
            chunk_query = select(DocumentChunk).where(
                DocumentChunk.document_id.in_(public_doc_ids)
            ).limit(request.top_k)
            
            result = await db.execute(chunk_query)
            chunks = result.scalars().all()
            
            print(f"[Public Search] Found {len(chunks)} chunks directly from database")
            
            # Build doc_id to doc mapping
            doc_map = {d.id: d for d in documents}
            
            for chunk in chunks:
                doc = doc_map.get(chunk.document_id)
                all_results.append({
                    "chunk_id": chunk.id,
                    "document_id": chunk.document_id,
                    "document_name": doc.name if doc else "Unknown",
                    "chunk_index": chunk.chunk_index,
                    "content": chunk.content,
                    "score": 0.5,  # Default score for fallback results
                    "tenant_id": doc.tenant_id if doc else "",
                })
        except Exception as e:
            print(f"[Public Search] Error in fallback search: {e}")
            import traceback
            traceback.print_exc()
    
    # Sort by score and limit results
    all_results.sort(key=lambda x: x.get("score", 0), reverse=True)
    all_results = all_results[:request.top_k]
    
    # Build response
    results = [
        PublicSearchResult(
            chunk_id=r.get("chunk_id", ""),
            document_id=r.get("document_id", ""),
            document_name=r.get("document_name", "Unknown"),
            chunk_index=r.get("chunk_index", 0),
            content=r.get("content", ""),
            score=r.get("score", 0),
            tenant_id=r.get("tenant_id", ""),
        )
        for r in all_results
    ]
    
    return BaseResponse(
        data=PublicSearchResponse(
            results=results,
            total=len(results),
            query=request.query,
        ),
    )


@router.get("/documents", response_model=BaseResponse[PublicDocumentListResponse])
async def list_public_documents(
    db: Annotated[AsyncSession, Depends(get_db)],
    tenantId: str | None = Query(default=None, description="Filter by tenant ID"),
    pageNum: int = Query(default=1, ge=1, description="Page number"),
    pageSize: int = Query(default=20, ge=1, le=100, description="Page size"),
    keyword: str | None = Query(default=None, description="Search keyword"),
):
    """
    List public documents without authentication.
    
    - If tenantId is provided, list only that tenant's public documents
    - If tenantId is not provided, list all public documents
    """
    documents, total = await get_public_documents(
        db,
        tenant_id=tenantId,
        page_num=pageNum,
        page_size=pageSize,
        keyword=keyword,
    )
    
    items = [
        PublicDocumentResponse(
            document_id=d.id,
            name=d.name,
            file_type=d.file_type,
            file_size=d.file_size,
            tenant_id=d.tenant_id,
            visibility=d.visibility,
            chunk_count=d.chunk_count,
            created_at=d.created_at.isoformat() if d.created_at else "",
        )
        for d in documents
    ]
    
    return BaseResponse(
        data=PublicDocumentListResponse(
            items=items,
            total=total,
            page_num=pageNum,
            page_size=pageSize,
        ),
    )


@router.get("/documents/{documentId}/chunks", response_model=BaseResponse)
async def get_public_document_chunks(
    documentId: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    pageNum: int = Query(default=1, ge=1, description="Page number"),
    pageSize: int = Query(default=20, ge=1, le=100, description="Page size"),
):
    """
    Get chunks of a public document without authentication.
    
    Only returns chunks if the document is public.
    """
    # First verify the document is public
    result = await db.execute(
        select(Document).where(
            Document.id == documentId,
            Document.visibility == "public",
            Document.status == "completed",
        )
    )
    doc = result.scalar_one_or_none()
    
    if doc is None:
        raise HTTPException(status_code=404, detail="Public document not found")
    
    # Get chunks
    query = select(DocumentChunk).where(DocumentChunk.document_id == documentId)
    
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    query = query.order_by(DocumentChunk.chunk_index.asc())
    query = query.offset((pageNum - 1) * pageSize).limit(pageSize)
    
    result = await db.execute(query)
    chunks = result.scalars().all()
    
    items = [
        {
            "chunkId": c.id,
            "chunkIndex": c.chunk_index,
            "content": c.content,
            "tokenCount": c.token_count,
        }
        for c in chunks
    ]
    
    return BaseResponse(
        data={
            "items": items,
            "total": total,
            "pageNum": pageNum,
            "pageSize": pageSize,
        },
    )
