"""Local manually supplied exchange rates only; contains no remote connector."""
from datetime import date
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException
from app.models.exchange_rate import ExchangeRate


class ExchangeRateService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_rate(self, dt: date, from_ccy: str, to_ccy: str = "CNY") -> float:
        if from_ccy == to_ccy:
            return 1.0
        result = await self.db.execute(select(ExchangeRate.rate).where(
            ExchangeRate.date == dt, ExchangeRate.from_ccy == from_ccy,
            ExchangeRate.to_ccy == to_ccy))
        rate = result.scalar_one_or_none()
        if rate is None:
            raise HTTPException(status_code=409, detail="离线版未设置该日期汇率，请先手动添加；不会调用外部服务或猜测汇率。")
        return float(rate)

    async def sync_latest_rates(self):
        raise HTTPException(status_code=403, detail="本地空数据版已禁用联网汇率同步。")

    async def batch_get_rates(self, pairs):
        return {(dt.isoformat(), ccy): await self.get_rate(dt, ccy) for dt, ccy in set(pairs)}
