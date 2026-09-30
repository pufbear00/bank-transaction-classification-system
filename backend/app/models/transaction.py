from sqlalchemy import Column, Integer, String, Float, Date, DateTime, Text, func
from app.database import Base


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    entity = Column(String(100), nullable=False, index=True, comment="公司实体")
    account = Column(String(100), nullable=False, index=True, comment="账户名称")
    counterpart = Column(String(200), nullable=True, comment="交易对方")
    period = Column(Date, nullable=False, index=True, comment="交易日期")
    abstract = Column(Text, nullable=True, comment="内容摘要")
    ccy = Column(String(10), nullable=False, comment="币种")
    cf = Column(Float, nullable=False, comment="现金流金额")
    bal = Column(Float, nullable=True, comment="余额")
    note = Column(Text, nullable=True, comment="备注")

    exchange_rate = Column(Float, default=1.0, comment="汇率")
    cf_in_cny = Column(Float, nullable=True, comment="折算人民币金额")

    management = Column(String(200), nullable=True, comment="Management分类")
    grouping = Column(String(200), nullable=True, comment="Grouping分类")
    class_name = Column(String(200), nullable=True, comment="Class分类")
    cf_line = Column(String(200), nullable=True, comment="现金流量表行项")
    classification_method = Column(String(50), nullable=True, comment="分类方法: keyword/ai/manual/learning")
    classification_confidence = Column(Float, nullable=True, comment="分类置信度")

    import_batch = Column(String(100), nullable=True, index=True, comment="导入批次ID")
    dedup_hash = Column(String(64), nullable=True, unique=True, comment="查重哈希")

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
