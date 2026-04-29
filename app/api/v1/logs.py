"""Log management API endpoints."""

from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import select, func
import csv
import io

from app.api.deps import DBSession, TenantAdmin
from app.models.log import QALog, AuditLog
from app.models.tool import ToolCallLog
from app.schemas import (
    BaseResponse,
    PaginatedResponse,
    QALogResponse,
    QALogListResponse,
    ToolLogResponse,
    AuditLogResponse,
)

router = APIRouter()


# ============ Audit Logs ============


@router.get("/audit", response_model=BaseResponse[PaginatedResponse[AuditLogResponse]])
async def list_audit_logs(
    db: DBSession,
    current_user: TenantAdmin,
    pageNum: int = Query(1, ge=1),
    pageSize: int = Query(20, ge=1),
    module: str | None = Query(None),
    action: str | None = Query(None),
    startTime: str | None = Query(None),
    endTime: str | None = Query(None),
    tenantId: str | None = Query(None),
):
    """List audit logs."""
    query = select(AuditLog)
    
    # Filter by tenant
    if current_user.role == "super_admin":
        if tenantId:
            query = query.where(AuditLog.tenant_id == tenantId)
    else:
        query = query.where(AuditLog.tenant_id == current_user.tenant_id)
    
    if module:
        query = query.where(AuditLog.module == module)
    if action:
        query = query.where(AuditLog.action == action)
    if startTime:
        query = query.where(AuditLog.created_at >= datetime.fromisoformat(startTime))
    if endTime:
        query = query.where(AuditLog.created_at <= datetime.fromisoformat(endTime))
    
    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # Get paginated results
    query = query.order_by(AuditLog.created_at.desc())
    query = query.offset((pageNum - 1) * pageSize).limit(pageSize)
    
    result = await db.execute(query)
    logs = result.scalars().all()
    
    items = [
        AuditLogResponse(
            logId=log.id,
            tenantId=log.tenant_id,
            operatorId=log.operator_id,
            operatorName=log.operator_name,
            module=log.module,
            action=log.action,
            targetType=log.target_type,
            targetId=log.target_id,
            detail=log.detail,
            createdAt=log.created_at,
        )
        for log in logs
    ]
    
    return BaseResponse(
        data=PaginatedResponse(items=items, total=total, pageNum=pageNum, pageSize=pageSize)
    )


# ============ QA Logs ============


@router.get("/qa", response_model=BaseResponse[PaginatedResponse[QALogListResponse]])
async def list_qa_logs(
    db: DBSession,
    current_user: TenantAdmin,
    pageNum: int = Query(1, ge=1),
    pageSize: int = Query(20, ge=1),
    keyword: str | None = Query(None),
    status: str | None = Query(None),
    startTime: str | None = Query(None),
    endTime: str | None = Query(None),
    tenantId: str | None = Query(None),
):
    """List QA logs."""
    query = select(QALog)
    
    # Filter by tenant
    if current_user.role == "super_admin":
        if tenantId:
            query = query.where(QALog.tenant_id == tenantId)
    else:
        query = query.where(QALog.tenant_id == current_user.tenant_id)
    
    if keyword:
        query = query.where(QALog.query.ilike(f"%{keyword}%"))
    if status:
        query = query.where(QALog.status == status)
    if startTime:
        query = query.where(QALog.created_at >= datetime.fromisoformat(startTime))
    if endTime:
        query = query.where(QALog.created_at <= datetime.fromisoformat(endTime))
    
    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # Get paginated results
    query = query.order_by(QALog.created_at.desc())
    query = query.offset((pageNum - 1) * pageSize).limit(pageSize)
    
    result = await db.execute(query)
    logs = result.scalars().all()
    
    items = [
        QALogListResponse(
            logId=log.id,
            sessionId=log.session_id,
            userId=log.user_id,
            query=log.query[:100] + "..." if len(log.query) > 100 else log.query,
            status=log.status,
            latencyMs=log.latency_ms,
            totalTokens=log.total_tokens,
            createdAt=log.created_at,
        )
        for log in logs
    ]
    
    return BaseResponse(
        data=PaginatedResponse(items=items, total=total, pageNum=pageNum, pageSize=pageSize)
    )


@router.get("/qa/{logId}", response_model=BaseResponse[QALogResponse])
async def get_qa_log(
    logId: str,
    db: DBSession,
    current_user: TenantAdmin,
):
    """Get QA log details."""
    result = await db.execute(select(QALog).where(QALog.id == logId))
    log = result.scalar_one_or_none()
    
    if not log:
        raise HTTPException(status_code=404, detail="日志不存在")
    
    # Check permission
    if current_user.role != "super_admin" and current_user.tenant_id != log.tenant_id:
        raise HTTPException(status_code=403, detail="无权限访问此日志")
    
    return BaseResponse(
        data=QALogResponse(
            logId=log.id,
            sessionId=log.session_id,
            userId=log.user_id,
            query=log.query,
            answer=log.answer,
            status=log.status,
            latencyMs=log.latency_ms,
            promptTokens=log.prompt_tokens,
            completionTokens=log.completion_tokens,
            totalTokens=log.total_tokens,
            sources=log.sources or [],
            toolCalls=log.tool_calls or [],
            createdAt=log.created_at,
        )
    )


# ============ Tool Logs ============


@router.get("/tools", response_model=BaseResponse[PaginatedResponse[ToolLogResponse]])
async def list_tool_logs(
    db: DBSession,
    current_user: TenantAdmin,
    pageNum: int = Query(1, ge=1),
    pageSize: int = Query(20, ge=1),
    toolId: str | None = Query(None),
    status: str | None = Query(None),
    startTime: str | None = Query(None),
    endTime: str | None = Query(None),
    tenantId: str | None = Query(None),
):
    """List tool call logs."""
    query = select(ToolCallLog)
    
    # Filter by tenant
    if current_user.role == "super_admin":
        if tenantId:
            query = query.where(ToolCallLog.tenant_id == tenantId)
    else:
        query = query.where(ToolCallLog.tenant_id == current_user.tenant_id)
    
    if toolId:
        query = query.where(ToolCallLog.tool_id == toolId)
    if status:
        query = query.where(ToolCallLog.status == status)
    if startTime:
        query = query.where(ToolCallLog.created_at >= datetime.fromisoformat(startTime))
    if endTime:
        query = query.where(ToolCallLog.created_at <= datetime.fromisoformat(endTime))
    
    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # Get paginated results
    query = query.order_by(ToolCallLog.created_at.desc())
    query = query.offset((pageNum - 1) * pageSize).limit(pageSize)
    
    result = await db.execute(query)
    logs = result.scalars().all()
    
    items = [
        ToolLogResponse(
            logId=log.id,
            toolId=log.tool_id,
            toolName=log.tool_name,
            sessionId=log.session_id,
            userId=log.user_id,
            status=log.status,
            latencyMs=log.latency_ms,
            errorMessage=log.error_message,
            createdAt=log.created_at,
        )
        for log in logs
    ]
    
    return BaseResponse(
        data=PaginatedResponse(items=items, total=total, pageNum=pageNum, pageSize=pageSize)
    )


@router.get("/tools/{logId}", response_model=BaseResponse[ToolLogResponse])
async def get_tool_log(
    logId: str,
    db: DBSession,
    current_user: TenantAdmin,
):
    """Get tool call log details."""
    result = await db.execute(select(ToolCallLog).where(ToolCallLog.id == logId))
    log = result.scalar_one_or_none()
    
    if not log:
        raise HTTPException(status_code=404, detail="日志不存在")
    
    # Check permission
    if current_user.role != "super_admin" and current_user.tenant_id != log.tenant_id:
        raise HTTPException(status_code=403, detail="无权限访问此日志")
    
    return BaseResponse(
        data=ToolLogResponse(
            logId=log.id,
            toolId=log.tool_id,
            toolName=log.tool_name,
            sessionId=log.session_id,
            userId=log.user_id,
            status=log.status,
            latencyMs=log.latency_ms,
            errorMessage=log.error_message,
            createdAt=log.created_at,
        )
    )


# ============ Export ============


@router.get("/export")
async def export_logs(
    db: DBSession,
    current_user: TenantAdmin,
    logType: str = Query(..., description="Log type: audit, qa, or tools"),
    startTime: str | None = Query(None),
    endTime: str | None = Query(None),
    tenantId: str | None = Query(None),
):
    """Export logs to CSV."""
    # Determine which log type to export
    if logType == "audit":
        model = AuditLog
        fields = ["id", "tenant_id", "operator_name", "module", "action", "target_type", "target_id", "created_at"]
    elif logType == "qa":
        model = QALog
        fields = ["id", "tenant_id", "user_id", "query", "answer", "status", "latency_ms", "total_tokens", "created_at"]
    elif logType == "tools":
        model = ToolCallLog
        fields = ["id", "tenant_id", "tool_name", "user_id", "status", "latency_ms", "error_message", "created_at"]
    else:
        raise HTTPException(status_code=400, detail="Invalid log type")
    
    query = select(model)
    
    # Filter by tenant
    if current_user.role == "super_admin":
        if tenantId:
            query = query.where(model.tenant_id == tenantId)
    else:
        query = query.where(model.tenant_id == current_user.tenant_id)
    
    if startTime:
        query = query.where(model.created_at >= datetime.fromisoformat(startTime))
    if endTime:
        query = query.where(model.created_at <= datetime.fromisoformat(endTime))
    
    query = query.order_by(model.created_at.desc()).limit(10000)
    
    result = await db.execute(query)
    logs = result.scalars().all()
    
    # Generate CSV
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(fields)
    
    for log in logs:
        row = [getattr(log, f, "") for f in fields]
        writer.writerow(row)
    
    output.seek(0)
    
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename={logType}_logs.csv"
        }
    )
