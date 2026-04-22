"""Response utilities."""

from typing import Any, TypeVar, Generic

from app.schemas.base import BaseResponse, PaginatedResponse

T = TypeVar("T")


def success_response(data: T | None = None, message: str = "success") -> BaseResponse[T]:
    """Create a success response."""
    return BaseResponse(code=0, message=message, data=data)


def error_response(code: int = 1, message: str = "error", data: Any = None) -> BaseResponse:
    """Create an error response."""
    return BaseResponse(code=code, message=message, data=data)


def paginated_response(
    items: list[T],
    total: int,
    page_num: int = 1,
    page_size: int = 20,
) -> PaginatedResponse[T]:
    """Create a paginated response."""
    return PaginatedResponse(
        list=items,
        total=total,
        pageNum=page_num,
        pageSize=page_size,
    )