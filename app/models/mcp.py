"""MCP models for MCP server management."""

from datetime import datetime

from sqlalchemy import func, DateTime, ForeignKey, String, Text, Integer, JSON, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin


class MCPServer(Base, TimestampMixin):
    """MCP server model."""

    __tablename__ = "mcp_servers"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    base_url: Mapped[str] = mapped_column(String(255), nullable=False)
    auth_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="none",
    )  # none, bearer, basic, api_key
    auth_config: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="enabled",
        index=True,
    )  # enabled, disabled
    timeout_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=20)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_check_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_check_status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="unknown",
    )  # success, failed, unknown
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
    tools: Mapped[list["MCPTool"]] = relationship(
        "MCPTool", back_populates="server", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<MCPServer(id={self.id}, name={self.name})>"


class MCPTool(Base, TimestampMixin):
    """MCP tool model."""

    __tablename__ = "mcp_tools"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    server_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("mcp_servers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tool_code: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    tool_name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    schema: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="enabled",
        index=True,
    )  # enabled, disabled
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
    server: Mapped["MCPServer"] = relationship("MCPServer", back_populates="tools")

    __table_args__ = (
        Index("ix_mcp_tools_server_code", "server_id", "tool_code", unique=True),
    )

    def __repr__(self) -> str:
        return f"<MCPTool(id={self.id}, tool_code={self.tool_code})>"