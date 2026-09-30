from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class ClassificationRuleBase(BaseModel):
    keyword: str
    management: str
    grouping: Optional[str] = None
    class_name: Optional[str] = None
    cf_line: Optional[str] = None
    source: Optional[str] = "manual"


class ClassificationRuleCreate(ClassificationRuleBase):
    pass


class ClassificationRuleUpdate(BaseModel):
    keyword: Optional[str] = None
    management: Optional[str] = None
    grouping: Optional[str] = None
    class_name: Optional[str] = None
    cf_line: Optional[str] = None


class ClassificationRuleResponse(ClassificationRuleBase):
    id: int
    match_count: int = 0
    confidence: Optional[float] = 1.0
    source: Optional[str] = "manual"
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
