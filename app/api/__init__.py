"""API module initialization."""

from fastapi import APIRouter

from app.api.v1 import auth, chat, documents, tenants, logs, tools, mcp, dashboard, monitor, health, users

api_router = APIRouter()

# Auth routes
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])

# Chat routes
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])

# Document routes
api_router.include_router(documents.router, prefix="/documents", tags=["documents"])

# User routes (admin: tenant_admin and super_admin)
api_router.include_router(users.router, prefix="/admin/users", tags=["admin-users"])

# Admin routes
api_router.include_router(tenants.router, prefix="/admin/tenants", tags=["admin-tenants"])
api_router.include_router(logs.router, prefix="/admin/logs", tags=["admin-logs"])
api_router.include_router(tools.router, prefix="/admin/tools", tags=["admin-tools"])
api_router.include_router(mcp.router, prefix="/admin/mcp", tags=["admin-mcp"])
api_router.include_router(dashboard.router, prefix="/admin/dashboard", tags=["admin-dashboard"])
api_router.include_router(monitor.router, prefix="/admin/monitor", tags=["admin-monitor"])

# System routes
api_router.include_router(health.router, tags=["system"])