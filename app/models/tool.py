"""Tool models for tool management."""

from datetime import datetime

from sqlalchemy import func, DateTime, ForeignKey, String, Text, Integer, JSON, Boolean, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin


class ToolDefinition(Base, TimestampMixin):
    """Tool definition model."""

    __tablename__ = "tool_definitions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )  # internal_api, database_query, http_service, mcp_tool
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="enabled",
        index=True,
    )  # enabled, disabled
    config: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    health_status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="unknown",
    )  # healthy, unhealthy, unknown
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    tenant_permissions: Mapped[list["TenantToolPermission"]] = relationship(
        "TenantToolPermission", back_populates="tool", cascade="all, delete-orphan"
    )
    call_logs: Mapped[list["ToolCallLog"]] = relationship(
        "ToolCallLog", back_populates="tool", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<ToolDefinition(id={self.id}, code={self.code}, name={self.name})>"


class TenantToolPermission(Base, TimestampMixin):
    """Tenant tool permission model."""

    __tablename__ = "tenant_tool_permissions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tool_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("tool_definitions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    config: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    tenant: Mapped["Tenant"] = relationship("Tenant", back_populates="tool_permissions")
    tool: Mapped["ToolDefinition"] = relationship("ToolDefinition", back_populates="tenant_permissions")

    __table_args__ = (
        Index("ix_tenant_tool_permissions_unique", "tenant_id", "tool_id", unique=True),
    )

    def __repr__(self) -> str:
        return f"<TenantToolPermission(tenant_id={self.tenant_id}, tool_id={self.tool_id})>"


class ToolCallLog(Base, TimestampMixin):
    """Tool call log model."""

    __tablename__ = "tool_call_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    session_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    message_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    tool_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("tool_definitions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    tool_name: Mapped[str] = mapped_column(String(100), nullable=False)
    request: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    response: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    latency_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="success",
        index=True,
    )  # success, failed
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    tool: Mapped["ToolDefinition"] = relationship("ToolDefinition", back_populates="call_logs")

    def __repr__(self) -> str:
        return f"<ToolCallLog(id={self.id}, tool_name={self.tool_name})>"