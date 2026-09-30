from sqlalchemy import Column, Integer, String, Float, Date, DateTime, Boolean, ForeignKey, func
from app.database import Base


class Amortization(Base):
    __tablename__ = "amortizations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    source_transaction_id = Column(Integer, ForeignKey("transactions.id"), nullable=True, comment="原始预付交易")
    entity = Column(String(100), nullable=False, index=True, comment="公司实体")
    total_amount = Column(Float, nullable=False, comment="摊销总额")
    start_date = Column(Date, nullable=False, comment="开始日期")
    months = Column(Integer, nullable=False, comment="摊销月数")
    monthly_amount = Column(Float, nullable=False, comment="每月摊销额")
    prepaid_account = Column(String(200), nullable=False, comment="预付科目(Management)")
    expense_account = Column(String(200), nullable=False, comment="费用科目(Management)")
    grouping = Column(String(200), nullable=True, comment="Grouping分类")
    class_name = Column(String(200), nullable=True, comment="Class分类")
    status = Column(String(20), nullable=False, default="active", comment="状态: active/completed")

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class AmortizationEntry(Base):
    __tablename__ = "amortization_entries"

    id = Column(Integer, primary_key=True, autoincrement=True)
    amortization_id = Column(Integer, ForeignKey("amortizations.id", ondelete="CASCADE"), nullable=False, index=True)
    period = Column(Date, nullable=False, comment="摊销月份")
    amount = Column(Float, nullable=False, comment="本期摊销额")
    is_posted = Column(Boolean, default=False, comment="是否已过账")
    debit_transaction_id = Column(Integer, ForeignKey("transactions.id"), nullable=True, comment="借方交易ID")
    credit_transaction_id = Column(Integer, ForeignKey("transactions.id"), nullable=True, comment="贷方交易ID")

    created_at = Column(DateTime(timezone=True), server_default=func.now())
