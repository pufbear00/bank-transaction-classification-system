from pydantic import BaseModel
from typing import Optional, Any, Dict
from datetime import datetime


class ImportTemplateBase(BaseModel):
    name: str
    bank_type: str
    description: Optional[str] = None
    config: Dict[str, Any]


class ImportTemplateCreate(ImportTemplateBase):
    pass


class ImportTemplateUpdate(BaseModel):
    name: Optional[str] = None
    bank_type: Optional[str] = None
    description: Optional[str] = None
    config: Optional[Dict[str, Any]] = None


class ImportTemplateResponse(ImportTemplateBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
