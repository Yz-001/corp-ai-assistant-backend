"""Custom exceptions for the application."""

from typing import Any


class AppException(Exception):
    """Base exception for application errors."""

    def __init__(
        self,
        code: int,
        message: str,
        status_code: int = 400,
        data: Any = None,
    ) -> None:
        self.code = code
        self.message = message
        self.status_code = status_code
        self.data = data
        super().__init__(message)


class UnauthorizedException(AppException):
    """Exception for unauthorized access."""

    def __init__(self, message: str = "未登录或token已过期") -> None:
        super().__init__(code=4001, message=message, status_code=401)


class ForbiddenException(AppException):
    """Exception for forbidden access."""

    def __init__(self, message: str = "无权限访问") -> None:
        super().__init__(code=4003, message=message, status_code=403)


class NotFoundException(AppException):
    """Exception for resource not found."""

    def __init__(self, message: str = "资源不存在") -> None:
        super().__init__(code=4004, message=message, status_code=404)


class BadRequestException(AppException):
    """Exception for bad request."""

    def __init__(self, message: str = "参数错误") -> None:
        super().__init__(code=4001, message=message, status_code=400)


class ConflictException(AppException):
    """Exception for conflict."""

    def __init__(self, message: str = "资源已存在") -> None:
        super().__init__(code=4002, message=message, status_code=409)


class ValidationException(AppException):
    """Exception for validation errors."""

    def __init__(self, message: str = "数据验证失败", errors: Any = None) -> None:
        super().__init__(code=4001, message=message, status_code=422, data=errors)


class ServerException(AppException):
    """Exception for server errors."""

    def __init__(self, message: str = "服务器内部错误") -> None:
        super().__init__(code=5000, message=message, status_code=500)


class RateLimitException(AppException):
    """Exception for rate limiting."""

    def __init__(self, message: str = "请求过于频繁，请稍后再试") -> None:
        super().__init__(code=4299, message=message, status_code=429)


class TenantDisabledException(AppException):
    """Exception for disabled tenant."""

    def __init__(self, message: str = "租户已被禁用") -> None:
        super().__init__(code=4003, message=message, status_code=403)


class UserDisabledException(AppException):
    """Exception for disabled user."""

    def __init__(self, message: str = "用户已被禁用") -> None:
        super().__init__(code=4003, message=message, status_code=403)


class DocumentProcessingException(AppException):
    """Exception for document processing errors."""

    def __init__(self, message: str = "文档处理失败") -> None:
        super().__init__(code=5001, message=message, status_code=500)


class ToolExecutionException(AppException):
    """Exception for tool execution errors."""

    def __init__(self, message: str = "工具执行失败") -> None:
        super().__init__(code=5002, message=message, status_code=500)


class MCPConnectionException(AppException):
    """Exception for MCP connection errors."""

    def __init__(self, message: str = "MCP服务连接失败") -> None:
        super().__init__(code=5003, message=message, status_code=500)