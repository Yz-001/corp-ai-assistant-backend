"""Auth schemas."""

from datetime import datetime

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    """Login request."""

    username: str = Field(min_length=1, max_length=50, description="Username")
    password: str = Field(min_length=1, max_length=100, description="Password")


class RefreshTokenRequest(BaseModel):
    """Refresh token request."""

    refresh_token: str = Field(alias="refreshToken", description="Refresh token")

    model_config = {"populate_by_name": True}


class UserInfoResponse(BaseModel):
    """User info response."""

    user_id: str = Field(alias="userId", description="User ID")
    username: str = Field(description="Username")
    email: str | None = Field(default=None, description="Email")
    role: str = Field(description="User role")
    tenant_id: str = Field(alias="tenantId", description="Tenant ID")
    tenant_name: str = Field(alias="tenantName", description="Tenant name")
    permissions: list[str] = Field(default_factory=list, description="Permissions")

    model_config = {"populate_by_name": True}


class TokenResponse(BaseModel):
    """Token response."""

    access_token: str = Field(alias="accessToken", description="Access token")
    refresh_token: str = Field(alias="refreshToken", description="Refresh token")
    expires_in: int = Field(alias="expiresIn", description="Expires in seconds")

    model_config = {"populate_by_name": True}


class LoginResponse(BaseModel):
    """Login response."""

    access_token: str = Field(alias="accessToken", description="Access token")
    refresh_token: str = Field(alias="refreshToken", description="Refresh token")
    expires_in: int = Field(alias="expiresIn", description="Expires in seconds")
    user_info: UserInfoResponse = Field(alias="userInfo", description="User info")

    model_config = {"populate_by_name": True}