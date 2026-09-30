from sqlalchemy import Column, Integer, String, Float, DateTime, func
from app.database import Base


class ClassificationRule(Base):
    __tablename__ = "classification_rules"

    id = Column(Integer, primary_key=True, autoincrement=True)
    keyword = Column(String(200), nullable=False, index=True, comment="匹配关键词")
    management = Column(String(200), nullable=False, comment="Management分类")
    grouping = Column(String(200), nullable=False, comment="Grouping分类")
    class_name = Column(String(200), nullable=False, comment="Class分类")
    cf_line = Column(String(200), nullable=True, comment="现金流量表行项")
    source = Column(String(50), default="manual", comment="来源: seed/manual/learned")
    match_count = Column(Integer, default=0, comment="命中次数")
    confidence = Column(Float, default=1.0, comment="置信度")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
