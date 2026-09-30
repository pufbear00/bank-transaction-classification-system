from sqlalchemy import Column, Integer, String, Float, Date, DateTime, func, UniqueConstraint
from app.database import Base


class AccountBalance(Base):
    """手动录入的账户期末余额，独立于交易表。"""
    __tablename__ = "account_balances"

    id = Column(Integer, primary_key=True, autoincrement=True)
    entity = Column(String(100), nullable=False)
    account = Column(String(100), nullable=False)
    period = Column(Date, nullable=False, comment="月末日期，如 2026-01-31")
    balance = Column(Float, nullable=False, comment="原币余额")
    ccy = Column(String(10), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("entity", "account", "period", name="uq_account_balance"),
    )
