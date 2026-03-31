from pydantic import BaseModel, Field
from enum import Enum
from typing import Optional

class PriorityEnum(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"

class UserCreateReport(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    attachment: Optional[str] = None
    category: Optional[str] = None
    priority: Optional[PriorityEnum] = None
class UserUpdateReport(BaseModel):
    title: str 
    description: str
    attachment: Optional[str] = Field(default=None, description="File URL or path")
    category: str
    priority: PriorityEnum = PriorityEnum.medium 
    

class ReportResponse(BaseModel):
    id: int
    title: str
    description: str
    attachment: str | None = None
    category: str
    priority: PriorityEnum
    class Config:
        from_attributes = True 

