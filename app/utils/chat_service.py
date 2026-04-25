"""Chat service for reusable chat logic."""

import json
import asyncio
from datetime import datetime
from typing import AsyncGenerator, Any
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from openai import AsyncOpenAI

from app.core.config import settings
from app.models.chat import ChatSession, ChatMessage
from app.models.document import Document, DocumentChunk
from app.utils.id import generate_id
from app.utils.rag_service import RAGService, build_rag_prompt


class ChatService:
    """Chat service for handling chat logic."""
    
    def __init__(self, db: AsyncSession, tenant_id: str):
        self.db = db
        self.tenant_id = tenant_id
        self.client = self._get_llm_client()
    
    def _get_llm_client(self) -> AsyncOpenAI | None:
        """Get LLM client if configured."""
        if not settings.openai_api_key:
            return None
        return AsyncOpenAI(
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url,
            timeout=120.0,
        )
    
    async def search_knowledge_base(
        self,
        query: str,
        include_private: bool = False,
        top_k: int = 5,
    ) -> tuple[str, list[dict]]:
        """
        Search knowledge base for relevant content.
        
        Args:
            query: Search query
            include_private: Whether to include private documents
            top_k: Number of results to return
            
        Returns:
            Tuple of (context_string, sources_list)
        """
        rag_service = RAGService(self.db, self.tenant_id)
        
        # Build visibility filter
        visibility_filter = None
        if not include_private:
            visibility_filter = "public"
        
        context, sources = await rag_service.build_context(
            query,
            visibility=visibility_filter,
            max_chunks=top_k,
        )
        
        return context, sources
    
    async def generate_precise_answer(
        self,
        query: str,
        include_private: bool = False,
    ) -> AsyncGenerator[dict, None]:
        """
        Generate precise answer from knowledge base (streaming).
        
        Args:
            query: User question
            include_private: Whether to include private documents
            
        Yields:
            SSE event data dicts
        """
        # Search knowledge base
        context, sources = await self.search_knowledge_base(
            query,
            include_private=include_private,
            top_k=3,
        )
        
        # If no context found, return friendly message
        if not context or not sources:
            yield {
                "event": "done",
                "data": {
                    "content": "抱歉，这个问题我暂时无法回答，您可以联系我们的专员为您解答，客服热线：400-882-6688",
                    "sources": [],
                }
            }
            return
        
        # Build prompt for precise answer
        prompt = f"""请根据以下参考资料精确回答用户的问题。要求：
1. 只回答问题相关的内容，不要扩展
2. 如果参考资料中有明确信息，直接提取关键信息回答
3. 回答简洁准确

参考资料：
{context}

用户问题：{query}

请精确回答："""
        
        response_text = ""
        
        if self.client:
            try:
                stream = await self.client.chat.completions.create(
                    model=settings.llm_model_name,
                    messages=[{"role": "user", "content": prompt}],
                    stream=True,
                    max_tokens=500,
                    temperature=0.3,
                )
                
                async for chunk in stream:
                    if chunk.choices and chunk.choices[0].delta.content:
                        content = chunk.choices[0].delta.content
                        response_text += content
                        yield {
                            "event": "token",
                            "data": {"content": content}
                        }
                        
            except Exception as e:
                yield {
                    "event": "error",
                    "data": {"message": f"生成回答时出错：{str(e)}"}
                }
                return
        else:
            # No API key
            yield {
                "event": "error",
                "data": {"message": "未配置 API Key"}
            }
            return
        
        # Send done event
        yield {
            "event": "done",
            "data": {
                "content": response_text,
                "sources": sources,
            }
        }
    
    async def generate_chat_answer(
        self,
        query: str,
        session_id: str | None = None,
        include_private: bool = False,
        user_id: str | None = None,
    ) -> AsyncGenerator[dict, None]:
        """
        Generate chat answer with full chat capabilities (streaming).
        
        Args:
            query: User question
            session_id: Chat session ID (optional, for multi-turn)
            include_private: Whether to include private documents
            user_id: User ID (optional, for logging)
            
        Yields:
            SSE event data dicts
        """
        # Send start event
        message_id = generate_id()
        yield {
            "event": "start",
            "data": {"messageId": message_id}
        }
        
        # Search knowledge base
        context, sources = await self.search_knowledge_base(
            query,
            include_private=include_private,
            top_k=5,
        )
        
        # Build RAG prompt
        rag_prompt = build_rag_prompt(query, context)
        
        response_text = ""
        prompt_tokens = 0
        completion_tokens = 0
        
        if self.client:
            try:
                stream = await self.client.chat.completions.create(
                    model=settings.llm_model_name,
                    messages=[
                        {
                            "role": "system",
                            "content": "你是AI企业助手，一个专业、友好的AI助手。请根据提供的参考资料准确回答用户的问题。如果参考资料中有相关信息，请优先使用；如果没有，可以根据你的知识回答，但要说明这不是来自文档资料。"
                        },
                        {"role": "user", "content": rag_prompt},
                    ],
                    stream=True,
                )
                
                async for chunk in stream:
                    if chunk.choices and chunk.choices[0].delta.content:
                        content = chunk.choices[0].delta.content
                        response_text += content
                        yield {
                            "event": "token",
                            "data": {"content": content}
                        }
                    
                    if hasattr(chunk, 'usage') and chunk.usage:
                        prompt_tokens = chunk.usage.prompt_tokens or 0
                        completion_tokens = chunk.usage.completion_tokens or 0
                        
            except Exception as e:
                yield {
                    "event": "error",
                    "data": {"message": f"调用AI服务时出错：{str(e)}"}
                }
                return
        else:
            # No API key
            fallback_msg = "您好！我是AI企业助手。当前未配置API Key。"
            for char in fallback_msg:
                yield {
                    "event": "token",
                    "data": {"content": char}
                }
                await asyncio.sleep(0.02)
            response_text = fallback_msg
        
        # Calculate tokens if not provided
        if not completion_tokens:
            completion_tokens = len(response_text)
        
        # Send done event
        yield {
            "event": "done",
            "data": {
                "messageId": message_id,
                "tokenUsage": {
                    "promptTokens": prompt_tokens,
                    "completionTokens": completion_tokens,
                    "totalTokens": prompt_tokens + completion_tokens,
                },
                "sources": sources,
            }
        }
    
    async def generate_session_title(self, user_query: str) -> str:
        """Generate a short title for the session based on user's first query."""
        if not self.client:
            return user_query[:20] + ("..." if len(user_query) > 20 else "")
        
        try:
            response = await self.client.chat.completions.create(
                model=settings.llm_model_name,
                messages=[
                    {"role": "system", "content": "你是一个标题生成助手。请根据用户的问题生成一个简短的标题（不超过15个字），只返回标题本身，不要加引号或其他符号。"},
                    {"role": "user", "content": user_query},
                ],
                max_tokens=20,
                temperature=0.7,
            )
            title = response.choices[0].message.content.strip()
            return title[:30] if len(title) > 30 else title
        except Exception:
            return user_query[:20] + ("..." if len(user_query) > 20 else "")