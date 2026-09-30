from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, func
from sqlalchemy.orm import relationship
from app.database import Base


class CategoryNode(Base):
    __tablename__ = "category_tree"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False, comment="节点名称")
    level = Column(Integer, nullable=False, comment="层级: 1=Grouping, 2=Class, 3=Management")
    parent_id = Column(Integer, ForeignKey("category_tree.id"), nullable=True)
    cf_line = Column(String(100), nullable=True, comment="现金流量表行项(仅L3)")
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    parent = relationship("CategoryNode", remote_side=[id], back_populates="children")
    children = relationship("CategoryNode", back_populates="parent", cascade="all, delete-orphan")
