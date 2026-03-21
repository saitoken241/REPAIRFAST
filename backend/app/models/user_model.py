from sqlalchemy import Column, Integer, String, Boolean
from ..database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    cpf = Column(String(11), unique=True, nullable=False, index=True)
    name = Column(String(100), index=True)
    email = Column(String(100), unique=True, nullable=False)
    role = Column(String(50), nullable=False) #Employee, analyst e manager
    number = Column(String(20), index=True, nullable=True)
    status_usuario = Column(Boolean, nullable=False, default=False) # False = off/True = On

    
