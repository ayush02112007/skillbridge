"""Shared response envelopes, pagination and filter primitives."""
from __future__ import annotations

import math
from typing import Annotated, Any, Generic, Literal, TypeVar

from fastapi import Query
from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class APIModel(BaseModel):
    """Base for every schema: ORM friendly, trims incoming strings."""

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        str_strip_whitespace=True,
        use_enum_values=False,
        validate_assignment=True,
    )


class ErrorDetail(BaseModel):
    code: str = Field(examples=["INTERNSHIP_NOT_FOUND"])
    message: str = Field(examples=["Internship not found"])
    details: Any | None = None


class ErrorResponse(BaseModel):
    """The single error shape returned by every endpoint."""

    success: Literal[False] = False
    error: ErrorDetail

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": False,
                "error": {
                    "code": "INTERNSHIP_NOT_FOUND",
                    "message": "Internship not found",
                },
            }
        }
    )


class Envelope(BaseModel, Generic[T]):
    success: Literal[True] = True
    data: T
    meta: dict[str, Any] | None = None


class PageMeta(BaseModel):
    page: int
    page_size: int
    total: int
    total_pages: int
    has_next: bool
    has_previous: bool


class Page(BaseModel, Generic[T]):
    success: Literal[True] = True
    data: list[T]
    meta: PageMeta

    @classmethod
    def build(cls, items: list[T], total: int, page: int, page_size: int) -> Page[T]:
        total_pages = max(1, math.ceil(total / page_size)) if page_size else 1
        return cls(
            data=items,
            meta=PageMeta(
                page=page,
                page_size=page_size,
                total=total,
                total_pages=total_pages,
                has_next=page < total_pages,
                has_previous=page > 1,
            ),
        )


class PaginationParams(BaseModel):
    page: int = 1
    page_size: int = 20

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size

    @property
    def limit(self) -> int:
        return self.page_size


def pagination(
    page: Annotated[int, Query(ge=1, description="1-indexed page number")] = 1,
    page_size: Annotated[int, Query(ge=1, le=100, description="Items per page")] = 20,
) -> PaginationParams:
    """FastAPI dependency providing consistent pagination across the API."""
    return PaginationParams(page=page, page_size=page_size)


class SortParams(BaseModel):
    sort_by: str | None = None
    sort_dir: Literal["asc", "desc"] = "desc"


def sorting(
    sort_by: Annotated[str | None, Query(description="Field to sort by")] = None,
    sort_dir: Annotated[Literal["asc", "desc"], Query()] = "desc",
) -> SortParams:
    return SortParams(sort_by=sort_by, sort_dir=sort_dir)


class MessageResponse(BaseModel):
    success: Literal[True] = True
    message: str


class IdResponse(BaseModel):
    id: str


def ok(data: Any, meta: dict[str, Any] | None = None) -> dict[str, Any]:
    """Build the success envelope for hand-rolled responses."""
    payload: dict[str, Any] = {"success": True, "data": data}
    if meta:
        payload["meta"] = meta
    return payload
