"""Chat API endpoints."""

from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import select, func
import json
import asyncio
from openai import AsyncOpenAI

from app.api.deps import DBSession, CurrentUser
from app.core.config import settings
from app.models.chat import ChatSession, ChatMessage
from app.models.prompt import PromptConfig
from app.schemas import (
    BaseResponse,
    PaginatedResponse,
    SessionCreate,
    SessionUpdate,
    SessionResponse,
    SessionListResponse,
    SessionDetailResponse,
    MessageCreate,
    MessageResponse,
    PromptResponse,
    SuggestionResponse,
)
from app.utils.id import generate_id
from app.utils.log_service import LogService
from app.utils.rag_service import RAGService, build_rag_prompt
from app.utils.tool_service import ToolExecutor

router = APIRouter()


def get_llm_client() -> AsyncOpenAI | None:
    """Get LLM client if configured."""
    if not settings.openai_api_key:
        return None
    return AsyncOpenAI(
        api_key=settings.openai_api_key,
        base_url=settings.openai_base_url,
        timeout=120.0,  # 2 minutes timeout
    )


@router.post("/sessions", response_model=BaseResponse[SessionResponse])
async def create_session(request: SessionCreate, current_user: CurrentUser, db: DBSession):
    """Create a new chat session."""
    session = ChatSession(
        id=generate_id(),
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
        title=request.title,
        channel=request.channel,
        status="active",
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)
    
    return BaseResponse(
        data=SessionResponse(
            sessionId=session.id,
            title=session.title,
            channel=session.channel,
            status=session.status,
            lastMessageAt=session.last_message_at,
            createdAt=session.created_at,
            updatedAt=session.updated_at,
        )
    )


@router.get("/sessions", response_model=BaseResponse[PaginatedResponse[SessionListResponse]])
async def get_sessions(
    current_user: CurrentUser,
    db: DBSession,
    pageNum: int = Query(1, ge=1),
    pageSize: int = Query(20, ge=1),
    keyword: str | None = Query(None),
):
    """Get user's chat sessions."""
    # Build query
    query = select(ChatSession).where(
        ChatSession.tenant_id == current_user.tenant_id,
        ChatSession.user_id == current_user.id,
        ChatSession.status != "deleted",
    )
    
    if keyword:
        query = query.where(ChatSession.title.ilike(f"%{keyword}%"))
    
    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # Get paginated results
    query = query.order_by(ChatSession.updated_at.desc())
    query = query.offset((pageNum - 1) * pageSize).limit(pageSize)
    
    result = await db.execute(query)
    sessions = result.scalars().all()
    
    items = [
        SessionListResponse(
            sessionId=s.id,
            title=s.title,
            lastMessageAt=s.last_message_at,
            updatedAt=s.updated_at,
        )
        for s in sessions
    ]
    
    return BaseResponse(
        data=PaginatedResponse(
            items=items,
            total=total,
            pageNum=pageNum,
            pageSize=pageSize,
        )
    )


@router.get("/sessions/{sessionId}", response_model=BaseResponse[SessionDetailResponse])
async def get_session(sessionId: str, current_user: CurrentUser, db: DBSession):
    """Get session details with messages."""
    result = await db.execute(
        select(ChatSession).where(
            ChatSession.id == sessionId,
            ChatSession.tenant_id == current_user.tenant_id,
            ChatSession.user_id == current_user.id,
        )
    )
    session = result.scalar_one_or_none()
    
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Get messages
    msg_result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.session_id == sessionId)
        .order_by(ChatMessage.created_at.asc())
    )
    messages = msg_result.scalars().all()
    
    msg_items = [
        MessageResponse(
            messageId=m.id,
            role=m.role,
            content=m.content,
            status=m.status,
            sources=m.sources or [],
            toolCalls=m.tool_calls or [],
            tokenUsage=m.token_usage,
            createdAt=m.created_at,
        )
        for m in messages
    ]
    
    # Return session with messages
    return BaseResponse(
        data=SessionDetailResponse(
            sessionId=session.id,
            title=session.title,
            channel=session.channel,
            status=session.status,
            lastMessageAt=session.last_message_at,
            createdAt=session.created_at,
            updatedAt=session.updated_at,
            messages=msg_items,
        )
    )


@router.patch("/sessions/{sessionId}", response_model=BaseResponse[SessionResponse])
async def update_session(
    sessionId: str,
    request: SessionUpdate,
    current_user: CurrentUser,
    db: DBSession,
):
    """Update session title."""
    result = await db.execute(
        select(ChatSession).where(
            ChatSession.id == sessionId,
            ChatSession.tenant_id == current_user.tenant_id,
            ChatSession.user_id == current_user.id,
        )
    )
    session = result.scalar_one_or_none()
    
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session.title = request.title
    await db.commit()
    await db.refresh(session)
    
    return BaseResponse(
        data=SessionResponse(
            sessionId=session.id,
            title=session.title,
            channel=session.channel,
            status=session.status,
            lastMessageAt=session.last_message_at,
            createdAt=session.created_at,
            updatedAt=session.updated_at,
        )
    )


@router.delete("/sessions/{sessionId}", response_model=BaseResponse)
async def delete_session(sessionId: str, current_user: CurrentUser, db: DBSession):
    """Delete a session."""
    result = await db.execute(
        select(ChatSession).where(
            ChatSession.id == sessionId,
            ChatSession.tenant_id == current_user.tenant_id,
            ChatSession.user_id == current_user.id,
        )
    )
    session = result.scalar_one_or_none()
    
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session.status = "deleted"
    await db.commit()
    
    return BaseResponse(message="Session deleted successfully")


@router.post("/messages", response_model=BaseResponse[MessageResponse])
async def send_message(request: MessageCreate, current_user: CurrentUser, db: DBSession):
    """Send a message (non-streaming)."""
    # Verify session
    result = await db.execute(
        select(ChatSession).where(
            ChatSession.id == request.session_id,
            ChatSession.tenant_id == current_user.tenant_id,
            ChatSession.user_id == current_user.id,
        )
    )
    session = result.scalar_one_or_none()
    
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Create user message
    user_msg = ChatMessage(
        id=generate_id(),
        tenant_id=current_user.tenant_id,
        session_id=request.session_id,
        role="user",
        content=request.query,
        status="done",
    )
    db.add(user_msg)
    
    # Create assistant message placeholder
    assistant_msg = ChatMessage(
        id=generate_id(),
        tenant_id=current_user.tenant_id,
        session_id=request.session_id,
        role="assistant",
        content="",
        status="generating",
    )
    db.add(assistant_msg)
    await db.commit()
    
    # TODO: Implement actual RAG logic here
    # For now, return a placeholder response
    assistant_msg.content = "这是一个示例回答。实际回答需要实现RAG逻辑。"
    assistant_msg.status = "done"
    assistant_msg.token_usage = {
        "promptTokens": 100,
        "completionTokens": 50,
        "totalTokens": 150,
    }
    await db.commit()
    await db.refresh(assistant_msg)
    
    # Update session last message time
    session.last_message_at = datetime.utcnow()
    await db.commit()
    
    return BaseResponse(
        data=MessageResponse(
            messageId=assistant_msg.id,
            role=assistant_msg.role,
            content=assistant_msg.content,
            status=assistant_msg.status,
            sources=assistant_msg.sources or [],
            toolCalls=assistant_msg.tool_calls or [],
            tokenUsage=assistant_msg.token_usage,
            createdAt=assistant_msg.created_at,
        )
    )


async def generate_session_title(client: AsyncOpenAI | None, user_query: str) -> str:
    """Generate a short title for the session based on user's first query."""
    if not client:
        # Fallback: use first 20 chars of query as title
        return user_query[:20] + ("..." if len(user_query) > 20 else "")
    
    try:
        response = await client.chat.completions.create(
            model=settings.llm_model_name,
            messages=[
                {"role": "system", "content": "你是一个标题生成助手。请根据用户的问题生成一个简短的标题（不超过15个字），只返回标题本身，不要加引号或其他符号。"},
                {"role": "user", "content": user_query},
            ],
            max_tokens=20,
            temperature=0.7,
        )
        title = response.choices[0].message.content.strip()
        # Limit to 30 chars
        return title[:30] if len(title) > 30 else title
    except Exception:
        # Fallback: use first 20 chars of query as title
        return user_query[:20] + ("..." if len(user_query) > 20 else "")


@router.post("/messages/stream")
async def send_message_stream(request: MessageCreate, current_user: CurrentUser, db: DBSession):
    """Send a message with streaming response."""
    print("=" * 60)
    print("[CHAT] 开始处理消息流请求")
    print(f"[CHAT] Session ID: {request.session_id}")
    print(f"[CHAT] User Query: {request.query[:100]}...")
    print(f"[CHAT] Tenant ID: {current_user.tenant_id}")
    print("=" * 60)
    
    # Verify session
    print("[CHAT] Step 1: 验证会话...")
    result = await db.execute(
        select(ChatSession).where(
            ChatSession.id == request.session_id,
            ChatSession.tenant_id == current_user.tenant_id,
            ChatSession.user_id == current_user.id,
        )
    )
    session = result.scalar_one_or_none()
    
    if session is None:
        print("[CHAT] ❌ 会话不存在或无权访问")
        raise HTTPException(status_code=404, detail="Session not found")
    
    print(f"[CHAT] ✅ 会话验证通过: {session.title}")
    
    # Check if this is the first message in the session (for auto title generation)
    existing_msgs = await db.execute(
        select(func.count()).where(ChatMessage.session_id == request.session_id)
    )
    is_first_message = (existing_msgs.scalar() or 0) == 0
    print(f"[CHAT] 是否首条消息: {is_first_message}")
    
    # Create user message
    print("[CHAT] Step 2: 保存用户消息...")
    user_msg = ChatMessage(
        id=generate_id(),
        tenant_id=current_user.tenant_id,
        session_id=request.session_id,
        role="user",
        content=request.query,
        status="done",
    )
    db.add(user_msg)
    await db.commit()
    print(f"[CHAT] ✅ 用户消息已保存: {user_msg.id}")
    
    # Get LLM client
    print("[CHAT] Step 3: 初始化LLM客户端...")
    client = get_llm_client()
    if client:
        print(f"[CHAT] ✅ LLM客户端已初始化: {settings.llm_model_name}")
        print(f"[CHAT]    Base URL: {settings.openai_base_url}")
    else:
        print("[CHAT] ⚠️ LLM客户端未初始化 (未配置API Key)")
    
    # Generate title for new session
    new_title = None
    if is_first_message and (session.title == "新会话" or not session.title):
        print("[CHAT] Step 4: 生成会话标题...")
        new_title = await generate_session_title(client, request.query)
        session.title = new_title
        await db.commit()
        print(f"[CHAT] ✅ 会话标题已生成: {new_title}")
    
    async def generate_stream():
        """Generate streaming response."""
        print("\n" + "=" * 60)
        print("[STREAM] 开始生成流式响应")
        print("=" * 60)
        
        assistant_msg_id = generate_id()
        
        # Send start event
        yield f"data: {json.dumps({'event': 'start', 'data': {'messageId': assistant_msg_id}})}\n\n"
        
        response_text = ""
        prompt_tokens = 0
        completion_tokens = 0
        sources = []
        
        # Get available tools for tenant
        print("[STREAM] Step 5: 检查可用工具...")
        tool_executor = ToolExecutor(db, current_user.tenant_id)
        available_tools = await tool_executor.get_available_tools()
        print(f"[STREAM]    租户可用工具数: {len(available_tools)}")
        
        tool_results = []
        if available_tools:
            print("[STREAM] Step 6: 让LLM决定是否调用工具...")
            for tool in available_tools:
                print(f"[STREAM]    - {tool['name']} (code: {tool['code']}, type: {tool['type']})")
            
            # Build tool definitions for LLM
            tool_definitions = []
            for tool in available_tools:
                tool_def = {
                    "type": "function",
                    "function": {
                        "name": tool['code'],
                        "description": tool['description'] or tool['name'],
                        "parameters": {
                            "type": "object",
                            "properties": {},
                            "required": []
                        }
                    }
                }
                # Add specific parameters based on tool type
                if tool['type'] == 'http_service':
                    config = tool.get('config', {})
                    url = config.get('url', '')
                    # Detect common parameters from URL template
                    if '{city}' in url or '{location}' in url:
                        tool_def["function"]["parameters"]["properties"]["city"] = {
                            "type": "string",
                            "description": "城市名称"
                        }
                        tool_def["function"]["parameters"]["required"].append("city")
                
                tool_definitions.append(tool_def)
            
            # First LLM call to decide if tools are needed
            try:
                tool_decision = await client.chat.completions.create(
                    model=settings.llm_model_name,
                    messages=[
                        {"role": "system", "content": "你是一个智能助手，可以调用工具来帮助用户。如果用户的问题需要使用工具（如查询天气、查询信息等），请调用相应的工具。否则直接回答。"},
                        {"role": "user", "content": request.query},
                    ],
                    tools=tool_definitions,
                    tool_choice="auto",
                )
                
                choice = tool_decision.choices[0]
                
                # Check if LLM wants to call tools
                if choice.message.tool_calls:
                    print(f"[STREAM] ✅ LLM决定调用 {len(choice.message.tool_calls)} 个工具")
                    
                    for tool_call in choice.message.tool_calls:
                        tool_code = tool_call.function.name
                        tool_args = json.loads(tool_call.function.arguments)
                        print(f"[STREAM]    调用工具: {tool_code}")
                        print(f"[STREAM]    参数: {json.dumps(tool_args, ensure_ascii=False)}")
                        
                        # Execute the tool
                        result = await tool_executor.execute_by_code(tool_code, tool_args)
                        print(f"[STREAM]    结果: {json.dumps(result, ensure_ascii=False)[:200]}...")
                        
                        tool_results.append({
                            "tool_code": tool_code,
                            "arguments": tool_args,
                            "result": result
                        })
                else:
                    print("[STREAM]    LLM决定不需要调用工具")
                    
            except Exception as e:
                print(f"[STREAM] ⚠️ 工具决策失败: {str(e)}")
        else:
            print("[STREAM]    租户没有可用工具，跳过工具调用")
        
        # Search for relevant document chunks (RAG)
        print("[STREAM] Step 7: RAG检索相关文档...")
        rag_service = RAGService(db, current_user.tenant_id)
        context, sources = await rag_service.build_context(request.query)
        print(f"[STREAM] ✅ RAG检索完成")
        print(f"[STREAM]    找到 {len(sources)} 个相关文档片段")
        if sources:
            for i, src in enumerate(sources[:3]):
                print(f"[STREAM]    - 来源{i+1}: {src.get('document_name', 'unknown')} (相关度: {src.get('score', 0):.2f})")
        
        # Build prompt with context and tool results
        print("[STREAM] Step 8: 构建提示词...")
        
        # Build enhanced prompt with tool results
        system_prompt = "你是AI企业助手，一个专业、友好的AI助手。请根据提供的参考资料和工具调用结果准确回答用户的问题。"
        
        user_content = request.query
        if context:
            user_content = f"参考资料：\n{context}\n\n用户问题：{request.query}"
        
        # Add tool results to prompt
        if tool_results:
            tool_info = "\n\n工具调用结果：\n"
            for tr in tool_results:
                tool_info += f"- {tr['tool_code']}: {json.dumps(tr['result'], ensure_ascii=False)}\n"
            user_content = tool_info + "\n" + user_content
        
        print(f"[STREAM] ✅ 提示词已构建 (长度: {len(user_content)} 字符)")
        
        if client:
            try:
                # Call LLM API with streaming
                print("[STREAM] Step 9: 调用LLM API...")
                print(f"[STREAM]    Model: {settings.llm_model_name}")
                print(f"[STREAM]    System: 你是AI企业助手...")
                print(f"[STREAM]    User prompt length: {len(user_content)}")
                
                stream = await client.chat.completions.create(
                    model=settings.llm_model_name,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_content},
                    ],
                    stream=True,
                )
                print("[STREAM] ✅ LLM API连接成功，开始接收流式响应...")
                
                chunk_count = 0
                async for chunk in stream:
                    if chunk.choices and chunk.choices[0].delta.content:
                        content = chunk.choices[0].delta.content
                        response_text += content
                        chunk_count += 1
                        if chunk_count % 20 == 0:
                            print(f"[STREAM]    已接收 {chunk_count} 个chunk, 累计 {len(response_text)} 字符")
                        yield f"data: {json.dumps({'event': 'token', 'data': {'content': content}})}\n\n"
                    
                    # Try to get usage info
                    if hasattr(chunk, 'usage') and chunk.usage:
                        prompt_tokens = chunk.usage.prompt_tokens or 0
                        completion_tokens = chunk.usage.completion_tokens or 0
                
                print(f"[STREAM] ✅ LLM响应完成")
                print(f"[STREAM]    总chunk数: {chunk_count}")
                print(f"[STREAM]    响应长度: {len(response_text)} 字符")
                print(f"[STREAM]    Prompt tokens: {prompt_tokens}")
                print(f"[STREAM]    Completion tokens: {completion_tokens}")
                
            except Exception as e:
                # Fallback to error message
                print(f"[STREAM] ❌ LLM调用失败: {str(e)}")
                error_msg = f"抱歉，调用AI服务时出错：{str(e)}"
                response_text = error_msg
                yield f"data: {json.dumps({'event': 'token', 'data': {'content': error_msg}})}\n\n"
        else:
            # No API key configured
            print("[STREAM] ⚠️ 未配置API Key，返回默认消息")
            fallback_msg = "您好！我是AI企业助手。当前未配置API Key，请设置环境变量 OPENAI_API_KEY。"
            response_text = fallback_msg
            for char in fallback_msg:
                yield f"data: {json.dumps({'event': 'token', 'data': {'content': char}})}\n\n"
                await asyncio.sleep(0.02)
        
        # Calculate tokens if not provided
        if not completion_tokens:
            completion_tokens = len(response_text)
        
        # Save assistant message
        print("[STREAM] Step 8: 保存助手消息...")
        assistant_msg = ChatMessage(
            id=assistant_msg_id,
            tenant_id=current_user.tenant_id,
            session_id=request.session_id,
            role="assistant",
            content=response_text,
            status="done",
            sources=sources,
            token_usage={
                "promptTokens": prompt_tokens,
                "completionTokens": completion_tokens,
                "totalTokens": prompt_tokens + completion_tokens,
            },
        )
        db.add(assistant_msg)
        
        # Update session last message time
        session.last_message_at = datetime.utcnow()
        await db.commit()
        print(f"[STREAM] ✅ 助手消息已保存: {assistant_msg_id}")
        
        # Record QA log
        print("[STREAM] Step 9: 记录QA日志...")
        log_service = LogService(db, current_user.tenant_id)
        await log_service.record_qa_log(
            query=request.query,
            answer=response_text,
            user_id=current_user.id,
            session_id=request.session_id,
            model_name=settings.llm_model_name,
            latency_ms=0,  # TODO: track actual latency
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            status="success",
        )
        print("[STREAM] ✅ QA日志已记录")
        
        # Send done event with optional new title and sources
        done_data = {
            'messageId': assistant_msg_id, 
            'tokenUsage': assistant_msg.token_usage,
            'sources': sources,
        }
        if new_title:
            done_data['title'] = new_title
        yield f"data: {json.dumps({'event': 'done', 'data': done_data})}\n\n"
        
        print("=" * 60)
        print("[STREAM] ✅ 消息流处理完成")
        print("=" * 60 + "\n")
    
    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


@router.get("/prompts", response_model=BaseResponse[PromptResponse])
async def get_prompts(
    current_user: CurrentUser,
    db: DBSession,
    channel: str = Query(default="web"),
):
    """Get prompt tags."""
    result = await db.execute(
        select(PromptConfig).where(
            PromptConfig.tenant_id == current_user.tenant_id,
            PromptConfig.channel == channel,
            PromptConfig.type == "tag",
            PromptConfig.enabled == True,
        ).order_by(PromptConfig.sort_order)
    )
    prompts = result.scalars().all()
    
    tags = [p.title for p in prompts]
    
    return BaseResponse(data=PromptResponse(tags=tags))


@router.get("/suggestions", response_model=BaseResponse[SuggestionResponse])
async def get_suggestions(
    current_user: CurrentUser,
    db: DBSession,
    channel: str = Query(default="web"),
):
    """Get suggested questions."""
    result = await db.execute(
        select(PromptConfig).where(
            PromptConfig.tenant_id == current_user.tenant_id,
            PromptConfig.channel == channel,
            PromptConfig.type == "suggested_question",
            PromptConfig.enabled == True,
        ).order_by(PromptConfig.sort_order)
    )
    prompts = result.scalars().all()
    
    suggestions = [p.content for p in prompts]
    
    return BaseResponse(data=SuggestionResponse(suggestions=suggestions))
