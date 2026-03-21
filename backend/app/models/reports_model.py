from sqlalchemy import Text,Enum,DateTime, Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from ..database import Base
from datetime import datetime

class Report(Base):
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True)
    title = Column(String(100), index=True, nullable=False)
    description = Column(Text, nullable=False)
    attachment = Column(String(255), nullable=True)
    category = Column(String(20), nullable=False, index=True)
    status = Column(
        Enum("open", 
             "closed", 
             "in_progress",
             name="status_enum"), 
        default="open", 
        nullable=False,
        index=True
        )
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    closed_at = Column(DateTime, nullable=True)
    priority = Column(
        Enum("low", 
             "medium", 
             "high", 
             name="priority_enum"),
          nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    user = relationship(
        "User",
        back_populates="reports"
    )
