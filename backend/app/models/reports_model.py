from sqlalchemy import Text, Enum, DateTime, Column, Integer, String, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from app.database import Base
from datetime import datetime

class Report(Base):
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True)
    title = Column(String(100), index=True, nullable=False)
    description = Column(Text, nullable=False)
    attachment = Column(Text, nullable=True)  # base64 data URL ou path
    category = Column(String(20), nullable=False, index=True)
    status = Column(
        Enum("open", "closed", "in_progress", name="status_enum"),
        default="open", nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=True)
    closed_at = Column(DateTime, nullable=True)
    priority = Column(
        Enum("low", "medium", "high", name="priority_enum"),
        default="medium", nullable=False, index=True)
    occurrence_type = Column(
        Enum("failure", "risk", "improvement", name="occurrence_type_enum"),
        nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    user = relationship("User", back_populates="reports", foreign_keys=[user_id])
    assigned_to = Column(Integer, ForeignKey("users.id"), nullable=True)
    assignee = relationship("User", foreign_keys=[assigned_to])
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=False, default=1)
    department = relationship("Department", back_populates="reports", foreign_keys=[department_id])
    history = relationship("ReportHistory", back_populates="report", cascade="all, delete-orphan", order_by="ReportHistory.created_at")
    action_plan = relationship("ActionPlan", back_populates="report", cascade="all, delete-orphan", order_by="ActionPlan.created_at")


class ReportHistory(Base):
    __tablename__ = "report_history"

    id          = Column(Integer, primary_key=True)
    report_id   = Column(Integer, ForeignKey("reports.id"), nullable=False, index=True)
    user_id     = Column(Integer, ForeignKey("users.id"), nullable=True)
    action      = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    comment     = Column(Text, nullable=True)
    color       = Column(String(30), nullable=True)
    created_at  = Column(DateTime, default=datetime.utcnow, nullable=False)

    report = relationship("Report", back_populates="history")
    user   = relationship("User", foreign_keys=[user_id])


class ActionPlan(Base):
    __tablename__ = "action_plan"

    id          = Column(Integer, primary_key=True)
    report_id   = Column(Integer, ForeignKey("reports.id"), nullable=False, index=True)
    assigned_to = Column(Integer, ForeignKey("users.id"), nullable=True)
    description = Column(Text, nullable=False)
    due_date    = Column(String(10), nullable=True)   # ISO date: YYYY-MM-DD
    done        = Column(Boolean, default=False, nullable=False)
    created_at  = Column(DateTime, default=datetime.utcnow, nullable=False)
    done_at     = Column(DateTime, nullable=True)

    report   = relationship("Report", back_populates="action_plan")
    assignee = relationship("User", foreign_keys=[assigned_to])