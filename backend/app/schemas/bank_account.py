from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class BankAccountBase(BaseModel):
    entity: str
    account: str
    account_number: Optional[str] = None
    ccy: str
    bank_type: Optional[str] = None


class BankAccountCreate(BankAccountBase):
    pass


class BankAccountUpdate(BaseModel):
    entity: Optional[str] = None
    account: Optional[str] = None
    account_number: Optional[str] = None
    ccy: Optional[str] = None
    bank_type: Optional[str] = None


class BankAccountResponse(BankAccountBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
