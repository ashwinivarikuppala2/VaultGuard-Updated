from datetime import datetime, timezone
from typing import Any, Generic, Optional, TypeVar
from pydantic import BaseModel, Field

DataType = TypeVar("DataType")


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: Optional[Any] = None


class ApiResponse(BaseModel, Generic[DataType]):
    success: bool = True
    data: Optional[DataType] = None
    message: Optional[str] = None
    error: Optional[ErrorDetail] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    trace_id: Optional[str] = None


def success_response(
    data: Any = None,
    trace_id: Optional[str] = None,
    message: Optional[str] = None,
) -> ApiResponse[Any]:
    return ApiResponse(
        success=True,
        data=data,
        message=message,
        error=None,
        timestamp=datetime.now(timezone.utc),
        trace_id=trace_id,
    )


def error_response(code: str, message: str, details: Optional[Any] = None, trace_id: Optional[str] = None) -> ApiResponse[Any]:
    return ApiResponse(
        success=False,
        data=None,
        error=ErrorDetail(code=code, message=message, details=details),
        timestamp=datetime.now(timezone.utc),
        trace_id=trace_id,
    )

