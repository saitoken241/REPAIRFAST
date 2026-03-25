from pydantic import BaseModel, Field, EmailStr 
from enum import Enum
from typing import Optional

class PriorityEnum(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"

class UserCreateReport(BaseModel):
    title: str 
    description: str
    attachment: Optional[str] = None
    category: str
    priority: PriorityEnum = PriorityEnum.medium 
class ReportResponse(BaseModel):
    id: int
    title: str
    description: str
    attachment: str | None = None
    category: str
    class Config:
        from_attributes = True 

