from pydantic import BaseModel
from typing import Optional, List
from datetime import date, datetime


class AmortizationCreate(BaseModel):
    entity: str
    total_amount: float
    start_date: date
    months: int
    prepaid_account: str
    expense_account: str
    grouping: Optional[str] = None
    class_name: Optional[str] = None
    source_transaction_id: Optional[int] = None


class AmortizationEntryResponse(BaseModel):
    id: int
    amortization_id: int
    period: date
    amount: float
    is_posted: bool
    debit_transaction_id: Optional[int] = None
    credit_transaction_id: Optional[int] = None
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class AmortizationResponse(BaseModel):
    id: int
    source_transaction_id: Optional[int] = None
    entity: str
    total_amount: float
    start_date: date
    months: int
    monthly_amount: float
    prepaid_account: str
    expense_account: str
    grouping: Optional[str] = None
    class_name: Optional[str] = None
    status: str
    posted_count: int = 0
    total_entries: int = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class AmortizationDetailResponse(AmortizationResponse):
    entries: List[AmortizationEntryResponse] = []
