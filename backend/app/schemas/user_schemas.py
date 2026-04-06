from pydantic import BaseModel, Field, EmailStr 
from enum import Enum
from typing import Optional

class UserRole(str, Enum):
    employee = "employee"
    analyst = "analyst"
    manager = "manager"


class UserCreate(BaseModel):
    name: str
    email: EmailStr
    cpf : str
    password: str = Field(min_length=6)
    company : str 
    number: str | None = None
    department_id: int 
    role: UserRole = UserRole.employee
    

class UserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    password: Optional[str] = None
    cpf: Optional[str] = None
    role: Optional[UserRole] = None
    number: Optional[str] = None
    department_id: Optional[int] = None
    

class UserResponse(BaseModel):
    id: int
    name: str
    email: str
    department_id: int
    class Config:
        from_attributes = True
    