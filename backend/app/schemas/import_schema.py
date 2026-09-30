from pydantic import BaseModel
from typing import Optional, List, Dict, Any


class ParseResponse(BaseModel):
    bank_type: str
    entity: str
    account: str
    total: int
    records: List[Dict[str, Any]]


class ConfirmImportRequest(BaseModel):
    records: List[Dict[str, Any]]
    entity: Optional[str] = None
    account: Optional[str] = None


class ConfirmImportResponse(BaseModel):
    batch_id: str
    imported: int
    duplicates: int
    classified: int
    unclassified: int
