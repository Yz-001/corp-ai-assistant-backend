"""Log service for recording QA, tool, and audit logs."""

import time
from datetime import datetime
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.log import QALog, AuditLog
from app.models.tool import ToolCallLog
from app.utils.id import generate_id


class LogService:
    """Service for recording various logs."""
    
    def __init__(self, db: AsyncSession, tenant_id: str):
        self.db = db
        self.tenant_id = tenant_id
    
    async def record_qa_log(
        self,
        query: str,
        answer: str | None,
        user_id: str | None = None,
        session_id: str | None = None,
        model_name: str | None = None,
        latency_ms: int = 0,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        sources: list[dict] | None = None,
        tool_calls: list[dict] | None = None,
        status: str = "success",
        error_message: str | None = None,
    ) -> QALog:
        """Record a QA log entry."""
        log = QALog(
            id=generate_id(),
            tenant_id=self.tenant_id,
            user_id=user_id,
            session_id=session_id,
            query=query,
            answer=answer,
            model_name=model_name,
            latency_ms=latency_ms,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
            source_count=len(sources) if sources else 0,
            sources=sources,
            tool_calls=tool_calls,
            status=status,
            error_message=error_message,
        )
        self.db.add(log)
        await self.db.commit()
        return log
    
    async def record_audit_log(
        self,
        module: str,
        action: str,
        operator_id: str | None = None,
        operator_name: str | None = None,
        target_type: str | None = None,
        target_id: str | None = None,
        detail: dict | None = None,
    ) -> AuditLog:
        """Record an audit log entry."""
        log = AuditLog(
            id=generate_id(),
            tenant_id=self.tenant_id,
            operator_id=operator_id,
            operator_name=operator_name,
            module=module,
            action=action,
            target_type=target_type,
            target_id=target_id,
            detail=detail,
        )
        self.db.add(log)
        await self.db.commit()
        return log
    
    async def record_tool_log(
        self,
        tool_id: str,
        tool_name: str,
        user_id: str | None = None,
        session_id: str | None = None,
        request: dict | None = None,
        response: dict | None = None,
        latency_ms: int = 0,
        status: str = "success",
        error_message: str | None = None,
    ) -> ToolCallLog:
        """Record a tool call log entry."""
        log = ToolCallLog(
            id=generate_id(),
            tenant_id=self.tenant_id,
            tool_id=tool_id,
            tool_name=tool_name,
            user_id=user_id,
            session_id=session_id,
            request=request,
            response=response,
            latency_ms=latency_ms,
            status=status,
            error_message=error_message,
        )
        self.db.add(log)
        await self.db.commit()
        return log


class QALatencyTracker:
    """Context manager to track QA latency."""
    
    def __init__(self):
        self.start_time = None
        self.latency_ms = 0
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, *args):
        end_time = time.time()
        self.latency_ms = int((end_time - self.start_time) * 1000)
        return False


# Convenience functions for common audit logs
async def log_login(db: AsyncSession, tenant_id: str, user_id: str, user_name: str):
    """Log user login."""
    service = LogService(db, tenant_id)
    return await service.record_audit_log(
        module="auth",
        action="login",
        operator_id=user_id,
        operator_name=user_name,
        target_type="user",
        target_id=user_id,
    )


async def log_logout(db: AsyncSession, tenant_id: str, user_id: str, user_name: str):
    """Log user logout."""
    service = LogService(db, tenant_id)
    return await service.record_audit_log(
        module="auth",
        action="logout",
        operator_id=user_id,
        operator_name=user_name,
        target_type="user",
        target_id=user_id,
    )


async def log_document_upload(
    db: AsyncSession, 
    tenant_id: str, 
    user_id: str, 
    user_name: str,
    document_id: str,
    document_name: str,
    file_size: int,
):
    """Log document upload."""
    service = LogService(db, tenant_id)
    return await service.record_audit_log(
        module="document",
        action="upload",
        operator_id=user_id,
        operator_name=user_name,
        target_type="document",
        target_id=document_id,
        detail={"fileName": document_name, "fileSize": file_size},
    )


async def log_document_delete(
    db: AsyncSession,
    tenant_id: str,
    user_id: str,
    user_name: str,
    document_id: str,
    document_name: str,
):
    """Log document delete."""
    service = LogService(db, tenant_id)
    return await service.record_audit_log(
        module="document",
        action="delete",
        operator_id=user_id,
        operator_name=user_name,
        target_type="document",
        target_id=document_id,
        detail={"fileName": document_name},
    )


async def log_tenant_create(
    db: AsyncSession,
    operator_id: str,
    operator_name: str,
    tenant_id: str,
    tenant_name: str,
):
    """Log tenant creation."""
    service = LogService(db, "default")  # System-level log
    return await service.record_audit_log(
        module="tenant",
        action="create",
        operator_id=operator_id,
        operator_name=operator_name,
        target_type="tenant",
        target_id=tenant_id,
        detail={"tenantName": tenant_name},
    )


async def log_tool_create(
    db: AsyncSession,
    tenant_id: str,
    user_id: str,
    user_name: str,
    tool_id: str,
    tool_name: str,
):
    """Log tool creation."""
    service = LogService(db, tenant_id)
    return await service.record_audit_log(
        module="tool",
        action="create",
        operator_id=user_id,
        operator_name=user_name,
        target_type="tool",
        target_id=tool_id,
        detail={"toolName": tool_name},
    )


async def log_mcp_server_create(
    db: AsyncSession,
    tenant_id: str,
    user_id: str,
    user_name: str,
    server_id: str,
    server_name: str,
):
    """Log MCP server creation."""
    service = LogService(db, tenant_id)
    return await service.record_audit_log(
        module="mcp",
        action="create",
        operator_id=user_id,
        operator_name=user_name,
        target_type="mcp_server",
        target_id=server_id,
        detail={"serverName": server_name},
    )