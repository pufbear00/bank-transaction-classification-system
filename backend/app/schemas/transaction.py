import math
from pydantic import BaseModel, field_validator
from typing import Optional, List
from datetime import date, datetime


def _clean_float(v):
    if v is None:
        return None
    if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
        return None
    return v


class TransactionBase(BaseModel):
    entity: str
    account: str
    counterpart: Optional[str] = None
    period: date
    abstract: Optional[str] = None
    ccy: str = "CNY"
    cf: float = 0
    bal: Optional[float] = None
    note: Optional[str] = None
    exchange_rate: Optional[float] = 1.0
    cf_in_cny: Optional[float] = None
    management: Optional[str] = None
    grouping: Optional[str] = None
    class_name: Optional[str] = None
    cf_line: Optional[str] = None
    classification_method: Optional[str] = None
    classification_confidence: Optional[float] = None

    @field_validator("cf", "bal", "cf_in_cny", "exchange_rate", "classification_confidence", mode="before")
    @classmethod
    def clean_nan(cls, v):
        return _clean_float(v)


class TransactionCreate(TransactionBase):
    pass


class TransactionUpdate(BaseModel):
    entity: Optional[str] = None
    account: Optional[str] = None
    counterpart: Optional[str] = None
    period: Optional[date] = None
    abstract: Optional[str] = None
    ccy: Optional[str] = None
    cf: Optional[float] = None
    bal: Optional[float] = None
    note: Optional[str] = None
    exchange_rate: Optional[float] = None
    cf_in_cny: Optional[float] = None
    management: Optional[str] = None
    grouping: Optional[str] = None
    class_name: Optional[str] = None
    cf_line: Optional[str] = None
    classification_method: Optional[str] = None
    classification_confidence: Optional[float] = None


class TransactionResponse(TransactionBase):
    id: int
    import_batch: Optional[str] = None
    dedup_hash: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class TransactionListResponse(BaseModel):
    items: List[TransactionResponse]
    total: int
    page: int
    page_size: int
    sum_cf: float = 0
    sum_cf_in_cny: float = 0


class BulkUpdateRequest(BaseModel):
    ids: List[int]
    entity: Optional[str] = None
    account: Optional[str] = None
    management: Optional[str] = None
    grouping: Optional[str] = None
    class_name: Optional[str] = None
    cf_line: Optional[str] = None
    classification_method: str = "manual"
