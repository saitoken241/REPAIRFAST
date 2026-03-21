from sqlalchemy import ForeignKey, Column, Integer, String, Boolean, Enum
from sqlalchemy.orm import relationship
from ..database import Base

#department of "employee","analyst","manager",


class Department(Base):
    __tablename__ = "departments"

    id = Column(Integer, primary_key=True)
    name = Column(String(50), nullable=False, unique=True)
    manager = Column(String(50), nullable=False, index=True)
    

    users = relationship(
        "User",
        back_populates="department"
        
)
    
