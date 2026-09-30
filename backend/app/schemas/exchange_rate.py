from pydantic import BaseModel
from typing import Optional
from datetime import date, datetime


class ExchangeRateBase(BaseModel):
    date: date
    from_ccy: str
    to_ccy: str = "CNY"
    rate: float
    source: str = "manual"


class ExchangeRateCreate(ExchangeRateBase):
    pass


class ExchangeRateUpdate(BaseModel):
    rate: Optional[float] = None
    source: Optional[str] = None


class ExchangeRateResponse(ExchangeRateBase):
    id: int
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
