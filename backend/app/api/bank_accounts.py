"""Bank Accounts CRUD API."""
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.dependencies import get_db
from app.models.bank_account import BankAccount
from app.schemas.bank_account import (
    BankAccountCreate, BankAccountUpdate, BankAccountResponse,
)

router = APIRouter(prefix="/bank-accounts", tags=["bank-accounts"])


@router.get("", response_model=List[BankAccountResponse])
async def list_bank_accounts(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(BankAccount).order_by(BankAccount.id))
    return [BankAccountResponse.model_validate(a) for a in result.scalars().all()]


@router.post("", response_model=BankAccountResponse)
async def create_bank_account(data: BankAccountCreate, db: AsyncSession = Depends(get_db)):
    account = BankAccount(**data.model_dump())
    db.add(account)
    await db.flush()
    return BankAccountResponse.model_validate(account)


@router.put("/{account_id}", response_model=BankAccountResponse)
async def update_bank_account(
    account_id: int, data: BankAccountUpdate, db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(BankAccount).where(BankAccount.id == account_id))
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail="Bank account not found")

    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(account, k, v)

    return BankAccountResponse.model_validate(account)


@router.delete("/{account_id}")
async def delete_bank_account(account_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(BankAccount).where(BankAccount.id == account_id))
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail="Bank account not found")

    await db.delete(account)
    return {"deleted": True}
