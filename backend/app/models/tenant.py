"""Tenant model."""

from datetime import datetime

from sqlalchemy import DateTime, String, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin


class Tenant(Base, TimestampMixin):
    """Tenant model for multi-tenant support."""

    __tablename__ = "tenants"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="enterprise",
        index=True,
    )  # public, sales, partner, enterprise
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="enabled",
        index=True,
    )  # enabled, disabled
    plan_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="basic",
    )  # basic, pro, enterprise
    quota_config: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    config: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default="now()",
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default="now()",
        onupdate="now()",
        nullable=False,
    )

    # Relationships
    users: Mapped[list["User"]] = relationship("User", back_populates="tenant")
    sessions: Mapped[list["ChatSession"]] = relationship(
        "ChatSession", back_populates="tenant", cascade="all, delete-orphan"
    )
    documents: Mapped[list["Document"]] = relationship(
        "Document", back_populates="tenant", cascade="all, delete-orphan"
    )
    prompt_configs: Mapped[list["PromptConfig"]] = relationship(
        "PromptConfig", back_populates="tenant", cascade="all, delete-orphan"
    )
    tool_permissions: Mapped[list["TenantToolPermission"]] = relationship(
        "TenantToolPermission", back_populates="tenant", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Tenant(id={self.id}, name={self.name}, code={self.code})>"

    @property
    def is_active(self) -> bool:
        """Check if tenant is active."""
        return self.status == "enabled"

    @property
    def is_public(self) -> bool:
        """Check if tenant is public."""
        return self.type == "public"