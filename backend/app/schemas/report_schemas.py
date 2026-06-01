from pydantic import BaseModel, Field, field_serializer
from enum import Enum
from typing import Optional, List
from datetime import datetime, timezone

class PriorityEnum(str, Enum):
    low    = "low"
    medium = "medium"
    high   = "high"

class StatusEnum(str, Enum):
    open        = "open"
    in_progress = "in_progress"
    closed      = "closed"

class UserCreateReport(BaseModel):
    title:           Optional[str]          = None
    description:     Optional[str]          = None
    attachment:      Optional[str]          = None
    category:        Optional[str]          = None
    priority:        Optional[PriorityEnum] = None
    occurrence_type: Optional[str]          = None
    department_id:   Optional[int]          = None
    sector:          Optional[str]          = None  # Nome do setor — usado pelo classificador Groq

class UserUpdateReport(BaseModel):
    title:           Optional[str]          = None
    description:     Optional[str]          = Field(default=None)
    attachment:      Optional[str]          = Field(default=None)
    category:        Optional[str]          = None
    priority:        Optional[PriorityEnum] = None
    status:          Optional[StatusEnum]   = None
    occurrence_type: Optional[str]          = None
    assigned_to:     Optional[int]          = None
    created_at:      Optional[datetime]     = None

class ReportHistoryCreate(BaseModel):
    action:      str
    description: Optional[str] = None
    comment:     Optional[str] = None
    color:       Optional[str] = None

class ReportHistoryResponse(BaseModel):
    id:          int
    report_id:   int
    action:      str
    description: Optional[str] = None
    comment:     Optional[str] = None
    color:       Optional[str] = None
    created_at:  datetime
    user_name:   Optional[str] = None
    model_config = {"from_attributes": True}

    @field_serializer("created_at")
    def serialize_created_at(self, v: datetime) -> str:
        if v is None:
            return None
        # Garante que o JS recebe o sufixo +00:00 para converter para horário local
        return v.isoformat() + ("+00:00" if v.utcoffset() is None else "")

# ── Plano de Ação ──
class ActionPlanCreate(BaseModel):
    description: str
    assigned_to: Optional[int] = None
    due_date:    Optional[str] = None   # YYYY-MM-DD

class ActionPlanUpdate(BaseModel):
    description: Optional[str]  = None
    assigned_to: Optional[int]  = None
    due_date:    Optional[str]   = None
    done:        Optional[bool]  = None

class ActionPlanResponse(BaseModel):
    id:            int
    report_id:     int
    description:   str
    assigned_to:   Optional[int]  = None
    assignee_name: Optional[str]  = None
    due_date:      Optional[str]  = None
    done:          bool
    created_at:    datetime
    done_at:       Optional[datetime] = None
    model_config = {"from_attributes": True}

class ReportResponse(BaseModel):
    id:               int
    title:            str
    description:      str
    attachment:       Optional[str]      = None
    category:         str
    priority:         PriorityEnum
    status:           StatusEnum
    occurrence_type:  Optional[str]      = None
    department_id:    Optional[int]      = None
    department_name:  Optional[str]      = None
    assigned_to:      Optional[int]      = None
    assigned_to_name: Optional[str]      = None
    created_at:       Optional[datetime] = None
    updated_at:       Optional[datetime] = None
    model_config = {"from_attributes": True}

class ReportCriticoResponse(BaseModel):
    id:         int
    title:      str
    department: Optional[str] = None
    status:     str
    reporter:   Optional[str] = None
    date:       str