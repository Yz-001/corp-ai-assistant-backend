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
from app.utils.tool_service import ToolExecutor


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
        
        # Check if we should use tools
        tool_executor = ToolExecutor(self.db, self.tenant_id)
        available_tools = await tool_executor.get_available_tools()
        
        print(f"[CHAT] 可用工具数: {len(available_tools)}")
        
        # Build tools for LLM if available
        tools_schema = None
        if available_tools:
            tools_schema = self._build_tools_schema(available_tools)
            print(f"[CHAT] 工具schema: {json.dumps(tools_schema, ensure_ascii=False)[:500]}")
        
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
                # Build messages
                messages = [
                    {
                        "role": "system",
                        "content": "你是AI企业助手，一个专业、友好的AI助手。请根据提供的参考资料准确回答用户的问题。如果参考资料中有相关信息，请优先使用；如果没有，可以根据你的知识回答，但要说明这不是来自文档资料。如果用户请求需要使用工具（如读取文件、访问网页等），请使用提供的工具。"
                    },
                    {"role": "user", "content": rag_prompt},
                ]
                
                # If tools available, first check if we need to call tools (non-streaming)
                if tools_schema:
                    print("[CHAT] 检查是否需要调用工具...")
                    first_response = await self.client.chat.completions.create(
                        model=settings.llm_model_name,
                        messages=messages,
                        tools=tools_schema,
                        tool_choice="auto",
                    )
                    
                    # Check if LLM wants to call a tool
                    if first_response.choices[0].message.tool_calls:
                        tool_calls = first_response.choices[0].message.tool_calls
                        print(f"[CHAT] LLM请求调用 {len(tool_calls)} 个工具")
                        
                        # Add assistant message with tool calls
                        messages.append(first_response.choices[0].message)
                        
                        # Execute each tool call
                        for tool_call in tool_calls:
                            tool_code = tool_call.function.name
                            tool_args = json.loads(tool_call.function.arguments)
                            
                            print(f"[CHAT] 执行工具: {tool_code}, 参数: {tool_args}")
                            
                            # Find tool in available_tools
                            tool_info = next((t for t in available_tools if t["code"] == tool_code), None)
                            
                            if tool_info:
                                # Execute tool
                                result = await tool_executor.execute(
                                    tool_info["tool_id"],
                                    tool_args,
                                    session_id,
                                    message_id,
                                )
                                
                                print(f"[CHAT] 工具结果: {json.dumps(result, ensure_ascii=False)[:500]}")
                                
                                # Add tool result to messages
                                messages.append({
                                    "role": "tool",
                                    "tool_call_id": tool_call.id,
                                    "content": json.dumps(result, ensure_ascii=False),
                                })
                            else:
                                messages.append({
                                    "role": "tool",
                                    "tool_call_id": tool_call.id,
                                    "content": json.dumps({"error": "工具不存在"}),
                                })
                        
                        # Now stream the final response
                        stream = await self.client.chat.completions.create(
                            model=settings.llm_model_name,
                            messages=messages,
                            stream=True,
                        )
                    else:
                        # No tool calls, stream directly
                        stream = await self.client.chat.completions.create(
                            model=settings.llm_model_name,
                            messages=messages,
                            stream=True,
                        )
                else:
                    # No tools, stream directly
                    stream = await self.client.chat.completions.create(
                        model=settings.llm_model_name,
                        messages=messages,
                        stream=True,
                    )
                
                # Stream response
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
    
    def _build_tools_schema(self, tools: list[dict]) -> list[dict]:
        """Build OpenAI tools schema from available tools."""
        schema = []
        for tool in tools:
            tool_type = tool.get("type", "")
            tool_code = tool.get("code", "")
            tool_name = tool.get("name", "")
            tool_desc = tool.get("description", "")
            config = tool.get("config", {})
            
            # Build parameters schema based on tool type
            parameters = {"type": "object", "properties": {}, "required": []}
            
            if tool_type == "mcp_tool":
                # MCP tools - generic parameters
                # Try to get schema from config
                if config.get("input_schema"):
                    parameters = config["input_schema"]
                else:
                    # Default: path or url parameter
                    parameters = {
                        "type": "object",
                        "properties": {
                            "path": {"type": "string", "description": "文件路径"},
                        },
                        "required": ["path"],
                    }
            
            elif tool_type == "web_scraper":
                parameters = {
                    "type": "object",
                    "properties": {
                        "url": {"type": "string", "description": "要爬取的网页URL"},
                    },
                    "required": ["url"],
                }
            
            elif tool_type == "http_service":
                # Extract parameters from URL template
                url = config.get("url", "")
                import re
                params = re.findall(r'\{(\w+)\}', url)
                for p in params:
                    parameters["properties"][p] = {"type": "string", "description": p}
                    parameters["required"].append(p)
            
            schema.append({
                "type": "function",
                "function": {
                    "name": tool_code,
                    "description": tool_desc or tool_name,
                    "parameters": parameters,
                }
            })
        
        return schema
