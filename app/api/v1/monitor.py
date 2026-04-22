"""System monitoring API endpoints."""

from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, Query
from sqlalchemy import select, func

from app.api.deps import DBSession, TenantAdmin
from app.models.log import QALog, ToolCallLog
from app.schemas import (
    BaseResponse,
    OnlineUsersResponse,
    TrafficResponse,
    TokensResponse,
    ErrorsResponse,
    ResponseTimeResponse,
)
from app.core.redis import get_online_users_count

router = APIRouter()


@router.get("/online-users", response_model=BaseResponse[OnlineUsersResponse])
async def get_online_users(
    db: DBSession,
    current_user: TenantAdmin,
):
    """Get current online users count."""
    online_count = await get_online_users_count()
    
    thirty_min_ago = datetime.utcnow() - timedelta(minutes=30)
    result = await db.execute(
        select(QALog.user_id).where(QALog.created_at >= thirty_min_ago).distinct()
    )
    active_count = len(result.scalars().all())
    
    return BaseResponse(
        data=OnlineUsersResponse(
            onlineUsers=online_count,
            activeUsers=active_count,
        )
    )


@router.get("/traffic", response_model=BaseResponse[list[TrafficResponse]])
async def get_traffic(
    db: DBSession,
    current_user: TenantAdmin,
    hours: int = Query(24, ge=1, le=168),
):
    """Get traffic statistics."""
    traffic = []
    now = datetime.utcnow()
    
    for i in range(hours - 1, -1, -1):
        hour_start = now - timedelta(hours=i + 1)
        hour_end = now - timedelta(hours=i)
        
        qa_result = await db.execute(
            select(func.count()).where(
                QALog.created_at >= hour_start,
                QALog.created_at < hour_end
            )
        )
        qa_count = qa_result.scalar() or 0
        
        tool_result = await db.execute(
            select(func.count()).where(
                ToolCallLog.created_at >= hour_start,
                ToolCallLog.created_at < hour_end
            )
        )
        tool_count = tool_result.scalar() or 0
        
        traffic.append(TrafficResponse(
            time=hour_start.strftime("%H:00"),
            requests=qa_count + tool_count,
        ))
    
    return BaseResponse(data=traffic)


@router.get("/tokens", response_model=BaseResponse[list[TokensResponse]])
async def get_tokens(
    db: DBSession,
    current_user: TenantAdmin,
    hours: int = Query(24, ge=1, le=168),
):
    """Get token usage statistics."""
    tokens = []
    now = datetime.utcnow()
    
    for i in range(hours - 1, -1, -1):
        hour_start = now - timedelta(hours=i + 1)
        hour_end = now - timedelta(hours=i)
        
        result = await db.execute(
            select(func.sum(QALog.total_tokens)).where(
                QALog.created_at >= hour_start,
                QALog.created_at < hour_end
            )
        )
        token_count = result.scalar() or 0
        
        tokens.append(TokensResponse(
            time=hour_start.strftime("%H:00"),
            tokens=token_count,
        ))
    
    return BaseResponse(data=tokens)


@router.get("/errors", response_model=BaseResponse[list[ErrorsResponse]])
async def get_errors(
    db: DBSession,
    current_user: TenantAdmin,
    hours: int = Query(24, ge=1, le=168),
):
    """Get error statistics."""
    errors = []
    now = datetime.utcnow()
    
    for i in range(hours - 1, -1, -1):
        hour_start = now - timedelta(hours=i + 1)
        hour_end = now - timedelta(hours=i)
        
        qa_error_result = await db.execute(
            select(func.count()).where(
                QALog.created_at >= hour_start,
                QALog.created_at < hour_end,
                QALog.status == "failed"
            )
        )
        qa_errors = qa_error_result.scalar() or 0
        
        tool_error_result = await db.execute(
            select(func.count()).where(
                ToolCallLog.created_at >= hour_start,
                ToolCallLog.created_at < hour_end,
                ToolCallLog.status == "failed"
            )
        )
        tool_errors = tool_error_result.scalar() or 0
        
        errors.append(ErrorsResponse(
            time=hour_start.strftime("%H:00"),
            errors=qa_errors + tool_errors,
        ))
    
    return BaseResponse(data=errors)


@router.get("/response-time", response_model=BaseResponse[list[ResponseTimeResponse]])
async def get_response_time(
    db: DBSession,
    current_user: TenantAdmin,
    hours: int = Query(24, ge=1, le=168),
):
    """Get response time statistics."""
    response_times = []
    now = datetime.utcnow()
    
    for i in range(hours - 1, -1, -1):
        hour_start = now - timedelta(hours=i + 1)
        hour_end = now - timedelta(hours=i)
        
        result = await db.execute(
            select(func.avg(QALog.latency_ms)).where(
                QALog.created_at >= hour_start,
                QALog.created_at < hour_end
            )
        )
        avg_latency = result.scalar() or 0
        
        response_times.append(ResponseTimeResponse(
            time=hour_start.strftime("%H:00"),
            avgLatencyMs=round(avg_latency),
        ))
    
    return BaseResponse(data=response_times)