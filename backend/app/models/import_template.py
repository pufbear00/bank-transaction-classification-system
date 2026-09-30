from sqlalchemy import Column, Integer, String, JSON, DateTime, func
from app.database import Base


class ImportTemplate(Base):
    __tablename__ = "import_templates"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, unique=True, comment="模板名称")
    bank_type = Column(String(50), nullable=False, comment="银行类型")
    description = Column(String(500), nullable=True)
    config = Column(JSON, nullable=False, comment="解析配置JSON")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
