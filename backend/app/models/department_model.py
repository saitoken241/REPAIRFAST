from sqlalchemy import ForeignKey, Column, Integer, String, Boolean, Enum
from sqlalchemy.orm import relationship
from ..database import Base

#department of "employee","analyst","manager",


class Department(Base):
    __tablename__ = "departments"

    id = Column(Integer, primary_key=True)
    name = Column(String(50), nullable=False, unique=True)
    manager_id = Column(Integer, ForeignKey("users.id"))
    

    reports = relationship(
        "Report",
        back_populates="department"
    )
    users = relationship(
        "User",
        back_populates="department",
        

)
    

    
