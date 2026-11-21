from typing import Generic, List, Optional, TypeVar
from pydantic import BaseModel, Field

ItemType = TypeVar("ItemType")


class PaginationParams(BaseModel):
    skip: int = Field(default=0, ge=0)
    limit: int = Field(default=50, ge=1, le=500)


class PaginatedResponse(BaseModel, Generic[ItemType]):
    items: List[ItemType]
    total: int
    skip: int
    limit: int

