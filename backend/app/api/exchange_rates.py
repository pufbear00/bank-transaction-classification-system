"""Exchange Rates CRUD API."""
from typing import List, Optional
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.dependencies import get_db
from app.models.exchange_rate import ExchangeRate
from app.schemas.exchange_rate import (
    ExchangeRateCreate, ExchangeRateUpdate, ExchangeRateResponse,
)
from app.services.exchange_rate_service import ExchangeRateService

router = APIRouter(prefix="/exchange-rates", tags=["exchange-rates"])


@router.post("/sync")
async def sync_rates(db: AsyncSession = Depends(get_db)):
    """手动触发同步所有活跃币种的今日汇率。"""
    svc = ExchangeRateService(db)
    rates = await svc.sync_latest_rates()
    return {"synced": rates}


@router.get("", response_model=List[ExchangeRateResponse])
async def list_rates(
    from_ccy: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: AsyncSession = Depends(get_db),
):
    q = select(ExchangeRate).order_by(ExchangeRate.date.desc())
    if from_ccy:
        q = q.where(ExchangeRate.from_ccy == from_ccy)
    if start_date:
        q = q.where(ExchangeRate.date >= start_date)
    if end_date:
        q = q.where(ExchangeRate.date <= end_date)
    result = await db.execute(q)
    return [ExchangeRateResponse.model_validate(r) for r in result.scalars().all()]


@router.post("", response_model=ExchangeRateResponse)
async def create_rate(data: ExchangeRateCreate, db: AsyncSession = Depends(get_db)):
    rate = ExchangeRate(**data.model_dump())
    db.add(rate)
    await db.flush()
    return ExchangeRateResponse.model_validate(rate)


@router.put("/{rate_id}", response_model=ExchangeRateResponse)
async def update_rate(
    rate_id: int, data: ExchangeRateUpdate, db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(ExchangeRate).where(ExchangeRate.id == rate_id))
    rate = result.scalar_one_or_none()
    if not rate:
        raise HTTPException(status_code=404, detail="Exchange rate not found")

    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(rate, k, v)

    return ExchangeRateResponse.model_validate(rate)


@router.delete("/{rate_id}")
async def delete_rate(rate_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ExchangeRate).where(ExchangeRate.id == rate_id))
    rate = result.scalar_one_or_none()
    if not rate:
        raise HTTPException(status_code=404, detail="Exchange rate not found")

    await db.delete(rate)
    return {"deleted": True}
