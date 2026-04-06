from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import SessionLocal
from ..models.reports_model import Report
from ..models.user_model import User
from ..schemas.report_schemas import UserCreateReport, ReportResponse, UserUpdateReport
from ..models.department_model import Department
from ..routers.auth import get_current_user
from ..routers.auth import require_roles


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

@router.get("/", response_model=list[ReportResponse])
def list_reports(db: Session = Depends(get_db),current_user: User = Depends(get_current_user)):
    if current_user.role in ("manager","analyst"):
        return db.query(Report).filter(
        Report.department_id == current_user.department_id
    ).all()
    else:
        return db.query(Report).filter(
        Report.user_id == current_user.id
     ).all()


@router.get("/{report_id}", response_model=ReportResponse)
def get_report(report_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    report = db.get(Report, report_id)

    
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    if current_user.role == "manager":
        if report.department_id != current_user.department_id:
            raise HTTPException(status_code=403, detail="Not authorized")
    else:
        if report.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized")

    return report



@router.put("/{report_id}", response_model=ReportResponse)
def update_report(
    report_id: int,
    report_data: UserUpdateReport,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    report = db.get(Report, report_id)

    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    if current_user.role == "manager":
        if report.department_id != current_user.department_id:
            raise HTTPException(status_code=403, detail="Not authorized")
    else:
        if report.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized")


    allowed_fields = ["title", "description", "attachment", "category", "priority"]

    for key, value in report_data.dict(exclude_unset=True).items():
        if key in allowed_fields:
            setattr(report, key, value)

    db.commit()
    db.refresh(report)

    return report

@router.delete("/{report_id}")
def delete_report(report_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    report = db.get(Report, report_id)

    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    # Manager → pode deletar do próprio departamento
    if current_user.role == "manager":
        if report.department_id != current_user.department_id:
            raise HTTPException(status_code=403, detail="Not authorized")

    # Employee → só pode deletar o próprio
    else:
        if report.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized")

    db.delete(report)
    db.commit()

    return {"detail": "Report deleted"}