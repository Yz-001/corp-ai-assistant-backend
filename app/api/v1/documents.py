"""Documents API endpoints."""

from fastapi import APIRouter, HTTPException, Query, UploadFile, File, Form
from sqlalchemy import select, func

from app.api.deps import DBSession, CurrentUser
from app.models.document import Document, DocumentChunk
from app.schemas import (
    BaseResponse,
    PaginatedResponse,
    DocumentUploadResponse,
    DocumentResponse,
    DocumentListResponse,
    DocumentChunkResponse,
)
from app.utils.id import generate_id

router = APIRouter()


@router.post("/upload", response_model=BaseResponse[DocumentUploadResponse])
async def upload_document(
    current_user: CurrentUser,
    db: DBSession,
    file: UploadFile = File(...),
    visibility: str = Form(default="private"),
    remark: str | None = Form(default=None),
):
    """Upload a document."""
    # Validate file type
    allowed_types = ["application/pdf", "application/msword", 
                     "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                     "text/plain", "text/markdown"]
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="File type not allowed")
    
    # Create document record
    doc = Document(
        id=generate_id(),
        tenant_id=current_user.tenant_id,
        name=file.filename or "unnamed",
        file_name=file.filename or "unnamed",
        file_type=file.content_type or "unknown",
        file_size=0,
        storage_path="",
        visibility=visibility,
        status="pending",
        created_by=current_user.id,
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)
    
    # TODO: Implement file storage and async processing
    
    return BaseResponse(
        data=DocumentUploadResponse(
            documentId=doc.id,
            status=doc.status,
        )
    )


@router.get("", response_model=BaseResponse[PaginatedResponse[DocumentListResponse]])
async def get_documents(
    current_user: CurrentUser,
    db: DBSession,
    pageNum: int = Query(1, ge=1),
    pageSize: int = Query(20, ge=1, le=100),
    keyword: str | None = Query(None),
    status: str | None = Query(None),
    fileType: str | None = Query(None),
):
    """Get documents list."""
    query = select(Document).where(Document.tenant_id == current_user.tenant_id)
    
    if keyword:
        query = query.where(Document.name.ilike(f"%{keyword}%"))
    if status:
        query = query.where(Document.status == status)
    if fileType:
        query = query.where(Document.file_type == fileType)
    
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    query = query.order_by(Document.created_at.desc())
    query = query.offset((pageNum - 1) * pageSize).limit(pageSize)
    
    result = await db.execute(query)
    docs = result.scalars().all()
    
    items = [
        DocumentListResponse(
            documentId=d.id,
            name=d.name,
            fileName=d.file_name,
            fileType=d.file_type,
            fileSize=d.file_size,
            tenantName=None,
            visibility=d.visibility,
            status=d.status,
            chunkCount=d.chunk_count,
            createdAt=d.created_at,
        )
        for d in docs
    ]
    
    return BaseResponse(
        data=PaginatedResponse(
            list=items,
            total=total,
            pageNum=pageNum,
            pageSize=pageSize,
        )
    )


@router.get("/{documentId}", response_model=BaseResponse[DocumentResponse])
async def get_document(documentId: str, current_user: CurrentUser, db: DBSession):
    """Get document details."""
    result = await db.execute(
        select(Document).where(
            Document.id == documentId,
            Document.tenant_id == current_user.tenant_id,
        )
    )
    doc = result.scalar_one_or_none()
    
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")
    
    return BaseResponse(
        data=DocumentResponse(
            documentId=doc.id,
            name=doc.name,
            fileName=doc.file_name,
            fileType=doc.file_type,
            fileSize=doc.file_size,
            tenantId=doc.tenant_id,
            tenantName=None,
            visibility=doc.visibility,
            status=doc.status,
            chunkCount=doc.chunk_count,
            createdBy=doc.created_by,
            errorMessage=doc.error_message,
            createdAt=doc.created_at,
            updatedAt=doc.updated_at,
        )
    )


@router.delete("/{documentId}", response_model=BaseResponse)
async def delete_document(documentId: str, current_user: CurrentUser, db: DBSession):
    """Delete a document."""
    result = await db.execute(
        select(Document).where(
            Document.id == documentId,
            Document.tenant_id == current_user.tenant_id,
        )
    )
    doc = result.scalar_one_or_none()
    
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")
    
    await db.delete(doc)
    await db.commit()
    
    return BaseResponse(message="Document deleted successfully")


@router.post("/{documentId}/retry", response_model=BaseResponse)
async def retry_document(documentId: str, current_user: CurrentUser, db: DBSession):
    """Retry document processing."""
    result = await db.execute(
        select(Document).where(
            Document.id == documentId,
            Document.tenant_id == current_user.tenant_id,
        )
    )
    doc = result.scalar_one_or_none()
    
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")
    
    if doc.status != "failed":
        raise HTTPException(status_code=400, detail="Document is not in failed status")
    
    doc.status = "pending"
    doc.error_message = None
    await db.commit()
    
    # TODO: Trigger async processing
    
    return BaseResponse(message="Document retry initiated")


@router.get("/{documentId}/chunks", response_model=BaseResponse[PaginatedResponse[DocumentChunkResponse]])
async def get_document_chunks(
    documentId: str,
    current_user: CurrentUser,
    db: DBSession,
    pageNum: int = Query(1, ge=1),
    pageSize: int = Query(20, ge=1, le=100),
):
    """Get document chunks."""
    result = await db.execute(
        select(Document).where(
            Document.id == documentId,
            Document.tenant_id == current_user.tenant_id,
        )
    )
    doc = result.scalar_one_or_none()
    
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")
    
    query = select(DocumentChunk).where(DocumentChunk.document_id == documentId)
    
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    query = query.order_by(DocumentChunk.chunk_index.asc())
    query = query.offset((pageNum - 1) * pageSize).limit(pageSize)
    
    result = await db.execute(query)
    chunks = result.scalars().all()
    
    items = [
        DocumentChunkResponse(
            chunkId=c.id,
            chunkIndex=c.chunk_index,