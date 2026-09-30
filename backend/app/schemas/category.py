from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class CategoryNodeBase(BaseModel):
    name: str
    level: int
    parent_id: Optional[int] = None
    cf_line: Optional[str] = None
    sort_order: int = 0


class CategoryNodeCreate(CategoryNodeBase):
    pass


class CategoryNodeUpdate(BaseModel):
    name: Optional[str] = None
    cf_line: Optional[str] = None
    sort_order: Optional[int] = None


class CategoryNodeResponse(CategoryNodeBase):
    id: int
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class CategoryTreeNode(CategoryNodeResponse):
    children: List["CategoryTreeNode"] = []


class CategoryLookupResponse(BaseModel):
    management: str
    class_name: Optional[str] = None
    grouping: Optional[str] = None
    cf_line: Optional[str] = None
