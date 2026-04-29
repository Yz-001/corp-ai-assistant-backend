from __future__ import annotations

"""User management schemas."""

from datetime import datetime

from pydantic import BaseModel, Field, EmailStr


class UserCreate(BaseModel):
    """User creation request."""

    username: str = Field(min_length=1, max_length=50, description="Username")
    password: str = Field(min_length=6, max_length=100, description="Password")
    email: str | None = Field(default=None, description="Email")
    role: str = Field(default="tenant_user", description="User role")
    tenant_id: str = Field(alias="tenantId", description="Tenant ID")

    model_config = {"populate_by_name": True}


class UserUpdate(BaseModel):
    """User update request."""

    email: str | None = Field(default=None, description="Email")
    role: str | None = Field(default=None, description="User role")
    status: str | None = Field(default=None, description="User status")


class UserPasswordUpdate(BaseModel):
    """User password update request."""

    old_password: str = Field(alias="oldPassword", description="Old password")
    new_password: str = Field(alias="newPassword", min_length=6, max_length=100, description="New password")

    model_config = {"populate_by_name": True}


class UserResponse(BaseModel):
    """User response."""

    user_id: str = Field(alias="userId", description="User ID")
    username: str = Field(description="Username")
    email: str | None = Field(default=None, description="Email")
    role: str = Field(description="User role")
    status: str = Field(description="User status")
    tenant_id: str = Field(alias="tenantId", description="Tenant ID")
    tenant_name: str | None = Field(default=None, alias="tenantName", description="Tenant name")
    last_login_at: datetime | None = Field(default=None, alias="lastLoginAt", description="Last login time")
    created_at: datetime = Field(alias="createdAt", description="Creation time")
    updated_at: datetime = Field(alias="updatedAt", description="Update time")

    model_config = {"populate_by_name": True}


class UserListResponse(BaseModel):
    """User list response item."""

    user_id: str = Field(alias="userId", description="User ID")
    username: str = Field(description="Username")
    email: str | None = Field(default=None, description="Email")
    role: str = Field(description="User role")
    status: str = Field(description="User status")
    tenant_id: str = Field(alias="tenantId", description="Tenant ID")
    tenant_name: str | None = Field(default=None, alias="tenantName", description="Tenant name")
    last_login_at: datetime | None = Field(default=None, alias="lastLoginAt", description="Last login time")
    created_at: datetime = Field(alias="createdAt", description="Creation time")

    model_config = {"populate_by_name": True}