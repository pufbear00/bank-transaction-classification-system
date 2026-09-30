from sqlalchemy import Column, Integer, String, DateTime, func
from app.database import Base


class BankAccount(Base):
    __tablename__ = "bank_accounts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    entity = Column(String(100), nullable=False, comment="公司实体")
    account = Column(String(100), nullable=False, comment="账户名称")
    account_number = Column(String(100), nullable=True, comment="银行账号")
    ccy = Column(String(10), nullable=False, comment="币种")
    bank_type = Column(String(50), nullable=True, comment="银行类型: cmb/citic/airwallex/dbs")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
