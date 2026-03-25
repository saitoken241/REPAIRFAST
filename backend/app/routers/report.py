from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import SessionLocal
from ..models.reports_model import Report
from ..models.user_model import User
from ..schemas.report_schemas import UserCreateReport, ReportResponse
from ..utils.security import hash_password
from ..models.department_model import Department
from ..routers.auth import get_current_user

router = APIRouter(
    prefix="/reports",
    tags=["Report"]
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/", response_model=ReportResponse)
def create_report(request: UserCreateReport, db: Session = Depends(get_db), current_user: User = Depends(get_current_user) ):
    new_report = Report(
        title=request.title,
        description=request.description,
        attachment=request.attachment,
        category=request.category,
        user_id=current_user.id,
        department_id=current_user.department_id
    )

    db.add(new_report)
    db.commit()
    db.refresh(new_report)
    
    return new_report
