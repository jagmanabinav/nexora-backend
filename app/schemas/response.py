"""Standard API response schemas."""

from typing import Any, Generic, Optional, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class ErrorDetail(BaseModel):
    """Error detail in response."""

    code: str
    message: str
    fields: list[dict[str, Any]] = Field(default_factory=list)


class PaginationInfo(BaseModel):
    """Pagination information."""

    page: int
    limit: int
    total: int
    total_pages: int


class SuccessResponse(BaseModel, Generic[T]):
    """Standard success response."""

    success: bool = True
    data: T
    message: str = "Operation completed successfully"
    request_id: str


class ListResponse(BaseModel, Generic[T]):
    """Standard list response with pagination."""

    success: bool = True
    data: list[T]
    pagination: PaginationInfo
    request_id: str


class ErrorResponse(BaseModel):
    """Standard error response."""

    success: bool = False
    error: ErrorDetail
    request_id: str
