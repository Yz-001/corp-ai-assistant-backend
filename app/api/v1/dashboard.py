"""Dashboard API endpoints."""

from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, Query
from sqlalchemy import select, func

from app.api.deps import DBSession, TenantAdmin
from app.models.log import QALog, ToolCallLog
from app.models.document import Document
from app.models.usage import UsageRecord
from app.schemas import (
    BaseResponse,
    DashboardOverviewResponse,
    TrendResponse,
    RankingResponse,
)

router = APIRouter()


@router.get("/overview", response_model=BaseResponse[DashboardOverviewResponse])
async def get_dashboard_overview(
    db: DBSession,
    current_user: TenantAdmin,
):
    """Get dashboard overview statistics."""
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    
    # Get today's QA count
    qa_today_result = await db.execute(
        select(func.count()).where(QALog.created_at >= today)
    )
    qa_today = qa_today_result.scalar() or 0
    
    # Get today's tool calls
    tool_calls_today_result = await db.execute(
        select(func.count()).where(ToolCallLog.created_at >= today)
    )
    tool_calls_today = tool_calls_today_result.scalar() or 0
    
    # Get today's documents
    docs_today_result = await db.execute(
        select(func.count()).where(Document.created_at >= today)
    )
    docs_today = docs_today_result.scalar() or 0
    
    # Get today's QA logs for token and latency calculation
    qa_logs_result = await db.execute(
        select(QALog).where(QALog.created_at >= today)
    )
    qa_logs = qa_logs_result.scalars().all()
    
    total_tokens = sum(log.total_tokens for log in qa_logs)
    total_latency = sum(log.latency_ms for log in qa_logs)
    fail_count = sum(1 for log in qa_logs if log.status == "failed")
    
    # Estimate online users (distinct users in last 5 min)
    five_min_ago = datetime.utcnow() - timedelta(minutes=5)
    recent_qa_result = await db.execute(
        select(QALog.user_id).where(QALog.created_at >= five_min_ago).distinct()
    )
    online_users = len(recent_qa_result.scalars().all())
    
    # Active users today
    active_users_result = await db.execute(
        select(QALog.user_id).where(QALog.created_at >= today).distinct()
    )
    active_users = len(active_users_result.scalars().all())
    
    return BaseResponse(
        data=DashboardOverviewResponse(
            onlineUsers=online_users,
            todayActiveUsers=active_users,
            todayQaCount=qa_today,
            todayRequestCount=qa_today + tool_calls_today,
            todayTokenCount=total_tokens,
            todayUploadCount=docs_today,
            todayToolCalls=tool_calls_today,
            errorRate=round(fail_count / qa_today, 4) if qa_today > 0 else 0,
            avgLatencyMs=round(total_latency / qa_today) if qa_today > 0 else 0,
        )
    )


@router.get("/trends", response_model=BaseResponse[list[TrendResponse]])
async def get_dashboard_trends(
    db: DBSession,
    current_user: TenantAdmin,
    days: int = Query(7, ge=1, le=30),
    type: str = Query("qa", description="Type: qa, tokens, or requests"),
):
    """Get dashboard trends."""
    trends = []
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    
    for i in range(days - 1, -1, -1):
        date = today - timedelta(days=i)
        next_date = date + timedelta(days=1)
        
        if type == "qa":
            result = await db.execute(
                select(func.count()).where(
                    QALog.created_at >= date,
                    QALog.created_at < next_date
                )
            )
            value = result.scalar() or 0
        elif type == "tokens":
            result = await db.execute(
                select(func.sum(QALog.total_tokens)).where(
                    QALog.created_at >= date,
                    QALog.created_at < next_date
                )
            )
            value = result.scalar() or 0
        elif type == "requests":
            qa_result = await db.execute(
                select(func.count()).where(
                    QALog.created_at >= date,
                    QALog.created_at < next_date
                )
            )
            tool_result = await db.execute(
                select(func.count()).where(
                    ToolCallLog.created_at >= date,
                    ToolCallLog.created_at < next_date
                )
            )
            value = (qa_result.scalar() or 0) + (tool_result.scalar() or 0)
        else:
            value = 0
        
        trends.append(TrendResponse(
            date=date.strftime("%Y-%m-%d"),
            value=value,
        ))
    
    return BaseResponse(data=trends)


@router.get("/rankings", response_model=BaseResponse[list[RankingResponse]])
async def get_dashboard_rankings(
    db: DBSession,
    current_user: TenantAdmin,
    type: str = Query("users", description="Type: users, tools, or queries"),
    limit: int = Query(10, ge=1, le=50),
):
    """Get dashboard rankings."""
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    
    if type == "users":
        # Top users by request count
        result = await db.execute(
            select(
                QALog.user_id,
                func.count().label("count")
            )
            .where(QALog.created_at >= today)
            .group_by(QALog.user_id)
            .order_by(func.count().desc())
            .limit(limit)
        )
        rankings = [
            RankingResponse(name=row.user_id or "Unknown", value=row.count)
            for row in result.all()
        ]
    elif type == "tools":
        # Top tools by call count
        result = await db.execute(
            select(
                ToolCallLog.tool_name,
                func.count().label("count")
            )
            .where(ToolCallLog.created_at >= today)
            .group_by(ToolCallLog.tool_name)
            .order_by(func.count().desc())
            .limit(limit)
        )
        rankings = [
            RankingResponse(name=row.tool_name or "Unknown", value=row.count)
            for row in result.all()
        ]
    elif type == "queries":
        # Top queries (this would need a separate table for popular queries)
        rankings = []
    else:
        rankings = []
    
    return BaseResponse(data=rankings)