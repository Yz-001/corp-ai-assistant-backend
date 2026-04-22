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
    MessageCreate,
    MessageResponse,
    PromptResponse,
    SuggestionResponse,
)
from app.utils.id import generate_id

router = APIRouter()


def get_llm_client() -> AsyncOpenAI | None:
    """Get LLM client if configured."""
    if not settings.openai_api_key:
        return None
    return AsyncOpenAI(
        api_key=settings.openai_api_key,
        base_url=settings.openai_base_url,
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
    pageSize: int = Query(20, ge=1, le=100),
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
            list=items,
            total=total,
            pageNum=pageNum,
            pageSize=pageSize,
        )
    )


@router.get("/sessions/{sessionId}")
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
        data={
            "sessionId": session.id,
            "title": session.title,
            "channel": session.channel,
            "status": session.status,
            "lastMessageAt": session.last_message_at,
            "createdAt": session.created_at,
            "updatedAt": session.updated_at,
            "messages": msg_items,
        }
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


@router.post("/messages/stream")
async def send_message_stream(request: MessageCreate, current_user: CurrentUser, db: DBSession):
    """Send a message with streaming response."""
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
    await db.commit()
    
    # Get LLM client
    client = get_llm_client()
    
    async def generate_stream():
        """Generate streaming response."""
        assistant_msg_id = generate_id()
        
        # Send start event
        yield f"data: {json.dumps({'event': 'start', 'data': {'messageId': assistant_msg_id}})}\n\n"
        
        response_text = ""
        prompt_tokens = 0
        completion_tokens = 0
        
        if client:
            try:
                # Call LLM API with streaming
                stream = await client.chat.completions.create(
                    model=settings.llm_model_name,
                    messages=[
                        {"role": "system", "content": "你是AI企业助手，一个专业、友好的AI助手。请用中文回答用户的问题。"},
                        {"role": "user", "content": request.query},
                    ],
                    stream=True,
                )
                
                async for chunk in stream:
                    if chunk.choices and chunk.choices[0].delta.content:
                        content = chunk.choices[0].delta.content
                        response_text += content
                        yield f"data: {json.dumps({'event': 'token', 'data': {'content': content}})}\n\n"
                    
                    # Try to get usage info
                    if hasattr(chunk, 'usage') and chunk.usage:
                        prompt_tokens = chunk.usage.prompt_tokens or 0
                        completion_tokens = chunk.usage.completion_tokens or 0
                
            except Exception as e:
                # Fallback to error message
                error_msg = f"抱歉，调用AI服务时出错：{str(e)}"
                response_text = error_msg
                yield f"data: {json.dumps({'event': 'token', 'data': {'content': error_msg}})}\n\n"
        else:
            # No API key configured
            fallback_msg = "您好！我是AI企业助手。当前未配置API Key，请设置环境变量 OPENAI_API_KEY。"
            response_text = fallback_msg
            for char in fallback_msg:
                yield f"data: {json.dumps({'event': 'token', 'data': {'content': char}})}\n\n"
                await asyncio.sleep(0.02)
        
        # Calculate tokens if not provided
        if not completion_tokens:
            completion_tokens = len(response_text)
        
        # Save assistant message
        assistant_msg = ChatMessage(
            id=assistant_msg_id,
            tenant_id=current_user.tenant_id,
            session_id=request.session_id,
            role="assistant",
            content=response_text,
            status="done",
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
        
        # Send done event
        yield f"data: {json.dumps({'event': 'done', 'data': {'messageId': assistant_msg_id, 'tokenUsage': assistant_msg.token_usage}})}\n\n"
    
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
