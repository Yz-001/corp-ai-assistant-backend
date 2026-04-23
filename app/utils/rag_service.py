"""RAG service for retrieving relevant document chunks."""

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document, DocumentChunk


class RAGService:
    """Service for RAG (Retrieval-Augmented Generation)."""
    
    def __init__(self, db: AsyncSession, tenant_id: str):
        self.db = db
        self.tenant_id = tenant_id
    
    async def search_relevant_chunks(
        self,
        query: str,
        top_k: int = 5,
    ) -> list[dict]:
        """Search for relevant document chunks based on query.
        
        Uses simple keyword matching for now. 
        TODO: Implement vector similarity search with embeddings.
        """
        # Get all completed documents for the tenant
        docs_result = await self.db.execute(
            select(Document).where(
                Document.tenant_id == self.tenant_id,
                Document.status == "completed",
            )
        )
        documents = docs_result.scalars().all()
        
        if not documents:
            return []
        
        doc_ids = [d.id for d in documents]
        doc_names = {d.id: d.name for d in documents}
        
        # Search chunks using simple keyword matching
        # Split query into keywords
        keywords = [k.strip() for k in query.split() if len(k.strip()) > 1]
        
        if not keywords:
            # If no meaningful keywords, return first few chunks
            result = await self.db.execute(
                select(DocumentChunk)
                .where(DocumentChunk.document_id.in_(doc_ids))
                .order_by(DocumentChunk.created_at.desc())
                .limit(top_k)
            )
            chunks = result.scalars().all()
        else:
            # Build OR conditions for keyword search
            # Use LIKE for simple text matching
            conditions = []
            for keyword in keywords:
                conditions.append(DocumentChunk.content.ilike(f"%{keyword}%"))
            
            # Search chunks that match any keyword
            from sqlalchemy import or_
            result = await self.db.execute(
                select(DocumentChunk)
                .where(
                    DocumentChunk.document_id.in_(doc_ids),
                    or_(*conditions),
                )
                .limit(top_k * 2)  # Get more for deduplication
            )
            chunks = result.scalars().all()
            
            # Score chunks by number of keyword matches
            scored_chunks = []
            for chunk in chunks:
                score = sum(1 for k in keywords if k.lower() in chunk.content.lower())
                scored_chunks.append((score, chunk))
            
            # Sort by score and take top_k
            scored_chunks.sort(key=lambda x: x[0], reverse=True)
            chunks = [c for _, c in scored_chunks[:top_k]]
        
        # Format results
        results = []
        for chunk in chunks:
            results.append({
                "chunk_id": chunk.id,
                "document_id": chunk.document_id,
                "document_name": doc_names.get(chunk.document_id, "Unknown"),
                "chunk_index": chunk.chunk_index,
                "content": chunk.content,
                "token_count": chunk.token_count,
            })
        
        return results
    
    async def build_context(
        self,
        query: str,
        max_chunks: int = 5,
        max_tokens: int = 2000,
    ) -> tuple[str, list[dict]]:
        """Build context string from relevant chunks.
        
        Returns:
            tuple: (context_string, sources_list)
        """
        chunks = await self.search_relevant_chunks(query, top_k=max_chunks)
        
        if not chunks:
            return "", []
        
        # Build context with token limit
        context_parts = []
        total_tokens = 0
        sources = []
        
        for chunk in chunks:
            chunk_tokens = chunk.get("token_count", len(chunk["content"]) // 2)
            
            if total_tokens + chunk_tokens > max_tokens:
                break
            
            context_parts.append(f"【文档：{chunk['document_name']}】\n{chunk['content']}")
            total_tokens += chunk_tokens
            
            sources.append({
                "documentId": chunk["document_id"],
                "documentName": chunk["document_name"],
                "chunkIndex": chunk["chunk_index"],
                "content": chunk["content"][:200] + "..." if len(chunk["content"]) > 200 else chunk["content"],
            })
        
        context = "\n\n---\n\n".join(context_parts)
        
        return context, sources


def build_rag_prompt(query: str, context: str) -> str:
    """Build a RAG prompt with context."""
    if not context:
        return query
    
    return f"""请根据以下参考资料回答用户的问题。如果参考资料中没有相关信息，请根据你的知识回答，但要说明这不是来自文档。

参考资料：
{context}

---
用户问题：{query}

请回答："""