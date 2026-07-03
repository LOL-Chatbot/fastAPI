from enum import Enum
from typing import Any

from pydantic import BaseModel


class Position(str, Enum):
    TOP = "TOP"
    JUNGLE = "JUNGLE"
    MID = "MID"
    ADC = "ADC"
    SUPPORT = "SUPPORT"


class Image(BaseModel):
    image_url: str | None = None
    image_key: str | None = None
    alt_text: str | None = None


class ErrorBody(BaseModel):
    code: str
    message: str


class SuccessResponse(BaseModel):
    success: bool = True
    data: Any
    message: str


class ErrorResponse(BaseModel):
    success: bool = False
    error: ErrorBody
