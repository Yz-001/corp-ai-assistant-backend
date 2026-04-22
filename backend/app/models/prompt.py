"""Prompt configuration model."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, Integer, Boolean, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin


class PromptConfig(Base, TimestampMixin):
    """Prompt configuration model for suggestions and tags."""

    __tablename__ = "prompt_configs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tenant_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )  # NULL means global
    scope: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="global",
        index=True,
    )  # global, tenant, channel
    channel: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="web",
    )  # web, public_widget, wecom
    type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        index=True,
    )  # tag, suggested_question
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
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
    tenant: Mapped["Tenant"] = relationship("Tenant", back_populates="prompt_configs")

    __table_args__ = (
        Index("ix_prompt_configs_scope_channel", "scope", "channel"),
    )

    def __repr__(self) -> str:
        return f"<PromptConfig(id={self.id}, type={self.type}, title={self.title})>"