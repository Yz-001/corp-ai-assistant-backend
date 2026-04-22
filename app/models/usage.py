"""Usage record model for statistics."""

from datetime import datetime

from sqlalchemy import func, DateTime, ForeignKey, String, Integer, Float, Date, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import TimestampMixin


class UsageRecord(Base, TimestampMixin):
    """Usage record model for tracking usage statistics."""

    __tablename__ = "usage_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    service_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )  # chat, tool, mcp, document
    request_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    token_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cost: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    stat_date: Mapped[datetime] = mapped_column(
        Date,
        nullable=False,
        index=True,
    )
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

    __table_args__ = (
        Index("ix_usage_records_tenant_date", "tenant_id", "stat_date"),
        Index("ix_usage_records_tenant_type_date", "tenant_id", "service_type", "stat_date"),
    )

    def __repr__(self) -> str:
        return f"<UsageRecord(id={self.id}, tenant_id={self.tenant_id}, service_type={self.service_type})>"