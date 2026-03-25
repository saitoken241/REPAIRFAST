from sqlalchemy import ForeignKey,Column, Integer, String, Boolean, Enum
from sqlalchemy.orm import relationship
from app.database import Base



class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    cpf = Column(String(11), unique=True, nullable=False, index=True)
    name = Column(String(100), index=True)
    email = Column(String(100), unique=True, nullable=False)
    password = Column(String(255), nullable=False)
    company = Column(String(100), nullable=False)
    role = Column(
    Enum(
        "employee",
        "analyst",
        "manager",
        name="role_enum"),
        nullable=False,
        default="manager"
        ) 
    number = Column(String(20), index=True, nullable=True)
    status_usuario = Column(Boolean, nullable=False, default=False) # False = off/True = On
    reports = relationship(
        "Report", 
        back_populates="user",
        cascade = "all, delete",
        uselist = True # 1:N
        )
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=False)

    department = relationship(
        "Department",
        back_populates="users",
        foreign_keys=[department_id],
        )
