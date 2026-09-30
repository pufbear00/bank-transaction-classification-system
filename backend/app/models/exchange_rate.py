from sqlalchemy import Column, Integer, String, Float, Date, DateTime, UniqueConstraint, func
from app.database import Base


class ExchangeRate(Base):
    __tablename__ = "exchange_rates"

    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(Date, nullable=False, index=True)
    from_ccy = Column(String(10), nullable=False)
    to_ccy = Column(String(10), nullable=False, default="CNY")
    rate = Column(Float, nullable=False)
    source = Column(String(50), default="frankfurter", comment="来源: frankfurter/manual/fallback")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("date", "from_ccy", "to_ccy", name="uq_rate_date_pair"),
    )
