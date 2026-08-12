from typing import Any, Optional

from pydantic import BaseModel


class ErrorDetail(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    success: bool = False
    timestamp: int
    error: ErrorDetail


class SuccessResponse(BaseModel):
    success: bool = True
    timestamp: int
    data: Any
    result1: Optional[Any] = None
    result2: Optional[Any] = None
