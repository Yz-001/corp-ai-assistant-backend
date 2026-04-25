"""RAG service for retrieving relevant document chunks using vector search."""

import os
import sys
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.document import Document, DocumentChunk

# Patch sqlite3 with pysqlite3 for ChromaDB compatibility (requires sqlite3 >= 3.35.0)
try:
    import pysqlite3 as sqlite3_module
    sys.modules["sqlite3"] = sqlite3_module
    print("[RAG] Using pysqlite3 for sqlite3 compatibility")
except ImportError:
    pass  # Fall back to system sqlite3

# Vector store imports
try:
    import chromadb
    from chromadb.config import Settings as ChromaSettings
    CHROMA_AVAILABLE = True
except (ImportError, RuntimeError) as e:
    print(f"[RAG] ChromaDB not available: {e}")
    CHROMA_AVAILABLE = False

# OpenAI client for embeddings
try:
    from openai import AsyncOpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False


class EmbeddingService:
    """Service for generating embeddings using OpenAI-compatible API."""
    
    def __init__(self):
        self.client = None
        if OPENAI_AVAILABLE and settings.openai_api_key:
            self.client = AsyncOpenAI(
                api_key=settings.openai_api_key,
                base_url=settings.openai_base_url,
            )
        self.model = settings.embedding_model_name
        self._cache: dict[str, list[float]] = {}
    
    async def get_embedding(self, text: str) -> list[float]:
        """Get embedding for a single text."""
        if not self.client:
            raise ValueError("OpenAI client not configured. Set OPENAI_API_KEY.")
        
        cache_key = text[:200]
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        try:
            response = await self.client.embeddings.create(
                model=self.model,
                input=text,
            )
            embedding = response.data[0].embedding
            self._cache[cache_key] = embedding
            return embedding
        except Exception as e:
            print(f"[Embedding] Error generating embedding: {e}")
            raise
    
    async def get_embeddings(self, texts: list[str]) -> list[list[float]]:
        """Get embeddings for multiple texts."""
        if not self.client:
            raise ValueError("OpenAI client not configured. Set OPENAI_API_KEY.")
        
        try:
            response = await self.client.embeddings.create(
                model=self.model,
                input=texts,
            )
            return [d.embedding for d in response.data]
        except Exception as e:
            print(f"[Embedding] Error generating embeddings: {e}")
            raise


class VectorStore:
    """Vector store using ChromaDB."""
    
    def __init__(self):
        self._client = None
        self._embedding_service = EmbeddingService()
    
    def _get_client(self):
        """Get or create ChromaDB client."""
        if self._client is None and CHROMA_AVAILABLE:
            persist_dir = settings.chroma_persist_dir
            os.makedirs(persist_dir, exist_ok=True)
            self._client = chromadb.PersistentClient(
                path=persist_dir,
                settings=ChromaSettings(
                    anonymized_telemetry=False,
                    allow_reset=True,
                )
            )
        return self._client
    
    def _get_collection(self, tenant_id: str):
        """Get or create collection for a tenant."""
        client = self._get_client()
        if client is None:
            return None
        collection_name = f"tenant_{tenant_id.replace('-', '_')}"
        try:
            return client.get_or_create_collection(
                name=collection_name,
                metadata={"tenant_id": tenant_id}
            )
        except Exception as e:
            print(f"[VectorStore] Error getting collection: {e}")
            return None
    
    async def add_chunks(self, tenant_id: str, chunks: list[dict]) -> bool:
        """Add document chunks to vector store."""
        collection = self._get_collection(tenant_id)
        if collection is None:
            print("[VectorStore] Collection not available")
            return False
        
        try:
            ids = [c["id"] for c in chunks]
            texts = [c["content"] for c in chunks]
            metadatas = [{
                "document_id": c["document_id"],
                "document_name": c["document_name"],
                "chunk_index": c["chunk_index"],
            } for c in chunks]
            
            embeddings = await self._embedding_service.get_embeddings(texts)
            
            collection.add(
                ids=ids,
                embeddings=embeddings,
                documents=texts,
                metadatas=metadatas,
            )
            print(f"[VectorStore] Added {len(chunks)} chunks to vector store")
            return True
        except Exception as e:
            print(f"[VectorStore] Error adding chunks: {e}")
            return False
    
    async def search(self, tenant_id: str, query: str, top_k: int = 5) -> list[dict]:
        """Search for similar chunks."""
        collection = self._get_collection(tenant_id)
        if collection is None:
            print("[VectorStore] Collection not available")
            return []
        
        try:
            query_embedding = await self._embedding_service.get_embedding(query)
            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                include=["documents", "metadatas", "distances"]
            )
            
            chunks = []
            if results["ids"] and results["ids"][0]:
                for i, chunk_id in enumerate(results["ids"][0]):
                    chunks.append({
                        "id": chunk_id,
                        "content": results["documents"][0][i] if results["documents"] else "",
                        "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                        "distance": results["distances"][0][i] if results["distances"] else 0,
                    })
            return chunks
        except Exception as e:
            print(f"[VectorStore] Error searching: {e}")
            return []
    
    def delete_document(self, tenant_id: str, document_id: str) -> bool:
        """Delete all chunks for a document."""
        collection = self._get_collection(tenant_id)
        if collection is None:
            return False
        try:
            results = collection.get(where={"document_id": document_id})
            if results["ids"]:
                collection.delete(ids=results["ids"])
                print(f"[VectorStore] Deleted {len(results['ids'])} chunks for document {document_id}")
            return True
        except Exception as e:
            print(f"[VectorStore] Error deleting document: {e}")
            return False


_vector_store: VectorStore | None = None


def get_vector_store() -> VectorStore:
    """Get or create vector store instance."""
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStore()
    return _vector_store


class RAGService:
    """Service for RAG (Retrieval-Augmented Generation)."""
    
    def __init__(self, db: AsyncSession, tenant_id: str):
        self.db = db
        self.tenant_id = tenant_id
        self.vector_store = get_vector_store()
    
    async def search_relevant_chunks(
        self,
        query: str,
        top_k: int = 5,
        visibility: str | None = None,
    ) -> list[dict]:
        """Search for relevant document chunks using vector similarity.
        
        Args:
            query: Search query
            top_k: Number of results to return
            visibility: Filter by visibility ('public' or None for all)
        """
        try:
            vector_results = await self.vector_store.search(self.tenant_id, query, top_k=top_k)
            if vector_results:
                print(f"[RAG] Vector search found {len(vector_results)} results")
                results = []
                
                # If visibility filter is set, get document visibility info
                doc_visibility = {}
                if visibility:
                    doc_ids = set()
                    for chunk in vector_results:
                        metadata = chunk.get("metadata", {})
                        doc_id = metadata.get("document_id", "")
                        if doc_id:
                            doc_ids.add(doc_id)
                    
                    if doc_ids:
                        doc_result = await self.db.execute(
                            select(Document.id, Document.visibility).where(
                                Document.id.in_(doc_ids)
                            )
                        )
                        for row in doc_result.fetchall():
                            doc_visibility[row[0]] = row[1]
                
                for chunk in vector_results:
                    metadata = chunk.get("metadata", {})
                    doc_id = metadata.get("document_id", "")
                    
                    # Apply visibility filter
                    if visibility and doc_id:
                        if doc_visibility.get(doc_id) != visibility:
                            continue
                    
                    results.append({
                        "chunk_id": chunk["id"],
                        "document_id": doc_id,
                        "document_name": metadata.get("document_name", "Unknown"),
                        "chunk_index": metadata.get("chunk_index", 0),
                        "content": chunk["content"],
                        "score": 1 - chunk.get("distance", 0),
                        "token_count": len(chunk["content"]) // 2,
                    })
                
                if results:
                    return results
        except Exception as e:
            print(f"[RAG] Vector search failed: {e}")
        
        # Fallback to database search
        print("[RAG] Falling back to database search")
        return await self._search_from_database(query, top_k, visibility)
    
    async def _search_from_database(
        self,
        query: str,
        top_k: int = 5,
        visibility: str | None = None,
    ) -> list[dict]:
        """Fallback: Search chunks from database using keyword matching.
        
        Args:
            query: Search query
            top_k: Number of results to return
            visibility: Filter by visibility ('public' or None for all)
        """
        doc_query = select(Document).where(
            Document.tenant_id == self.tenant_id,
            Document.status == "completed",
        )
        
        if visibility:
            doc_query = doc_query.where(Document.visibility == visibility)
        
        docs_result = await self.db.execute(doc_query)
        documents = docs_result.scalars().all()
        
        if not documents:
            return []
        
        doc_ids = [d.id for d in documents]
        doc_names = {d.id: d.name for d in documents}
        
        keywords = [k.strip() for k in query.split() if len(k.strip()) > 1]
        
        if not keywords:
            result = await self.db.execute(
                select(DocumentChunk)
                .where(DocumentChunk.document_id.in_(doc_ids))
                .order_by(DocumentChunk.created_at.desc())
                .limit(top_k)
            )
            chunks = result.scalars().all()
        else:
            from sqlalchemy import or_
            conditions = []
            for keyword in keywords:
                conditions.append(DocumentChunk.content.ilike(f"%{keyword}%"))
            
            result = await self.db.execute(
                select(DocumentChunk)
                .where(
                    DocumentChunk.document_id.in_(doc_ids),
                    or_(*conditions),
                )
                .limit(top_k * 2)
            )
            chunks = result.scalars().all()
            
            scored_chunks = []
            for chunk in chunks:
                score = sum(1 for k in keywords if k.lower() in chunk.content.lower())
                scored_chunks.append((score, chunk))
            
            scored_chunks.sort(key=lambda x: x[0], reverse=True)
            chunks = [c for _, c in scored_chunks[:top_k]]
        
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
        visibility: str | None = None,
    ) -> tuple[str, list[dict]]:
        """Build context string from relevant chunks.
        
        Args:
            query: Search query
            max_chunks: Maximum number of chunks to include
            max_tokens: Maximum total tokens
            visibility: Filter by visibility ('public' or None for all)
        """
        chunks = await self.search_relevant_chunks(query, top_k=max_chunks, visibility=visibility)
        
        if not chunks:
            return "", []
        
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
                "chunkId": chunk["chunk_id"],
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


async def index_document_chunks(
    tenant_id: str,
    document_id: str,
    document_name: str,
    chunks: list[dict],
) -> bool:
    """Index document chunks to vector store."""
    vector_store = get_vector_store()
    
    # Prepare chunks with metadata
    chunks_with_meta = []
    for chunk in chunks:
        chunks_with_meta.append({
            "id": chunk["id"],
            "content": chunk["content"],
            "document_id": document_id,
            "document_name": document_name,
            "chunk_index": chunk["chunk_index"],
        })
    
    return await vector_store.add_chunks(tenant_id, chunks_with_meta)
