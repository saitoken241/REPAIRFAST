from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import SessionLocal
from ..models.reports_model import Report
from ..models.user_model import User
from ..schemas.report_schemas import UserCreateReport, ReportResponse, UserUpdateReport, ReportCriticoResponse
from ..models.department_model import Department
from ..routers.auth import get_current_user
from ..routers.auth import require_roles
from sqlalchemy import func, case
from sqlalchemy.orm import joinedload

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
    
@router.get("/me/resumo")
def get_reports_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(
        func.count(Report.id).label("total"),
        func.sum(case((Report.status == "open", 1), else_=0)).label("aberto"),
        func.sum(case((Report.status == "in_progress", 1), else_=0)).label("andamento"),
        func.sum(case((Report.status == "closed", 1), else_=0)).label("resolvido"),
    )

    if current_user.role in ("manager", "analyst"):
        query = query.filter(Report.department_id == current_user.department_id)
    else:
        query = query.filter(Report.user_id == current_user.id)

    result = query.one()

    return {
        "total": result.total or 0,
        "aberto": result.aberto or 0,
        "andamento": result.andamento or 0,
        "resolvido": result.resolvido or 0,
    }

@router.get("/department/resume")
def get_department_reports_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role not in ("manager", "analyst"):
        raise HTTPException(403, "Not authorized")

    query = db.query(
        func.count(Report.id).label("total"),
        func.sum(case((Report.status == "open", 1), else_=0)).label("aberto"),
        func.sum(case((Report.status == "in_progress", 1), else_=0)).label("andamento"),
        func.sum(case((Report.status == "closed", 1), else_=0)).label("resolvido"),
    ).filter(Report.department_id == current_user.department_id)

    result = query.one()

    return {
        "total": result.total or 0,
        "aberto": result.aberto or 0,
        "andamento": result.andamento or 0,
        "resolvido": result.resolvido or 0,
    }



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

@router.get("/department/critical", response_model=list[ReportCriticoResponse])
def get_critical_reports_by_department(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    
    if current_user.role not in ("manager", "analyst"):
        raise HTTPException(status_code=403, detail="Not authorized")

    reports = db.query(Report).options(
        joinedload(Report.user),
        joinedload(Report.department)
    ).filter(
        Report.department_id == current_user.department_id,
        Report.priority == "high",
        Report.status != "closed"
    ).all()

    status_map = {
        "open": "aberto",
        "in_progress": "andamento",
        "closed": "resolvido"
    }

    return [
        {
            "id": r.id,
            "title": r.title,
            "department": r.department.name if r.department else None,
            "status": status_map.get(r.status, r.status),
            "reporter": r.user.name if r.user else None,
            "date": r.created_at.strftime("%d/%m/%Y") if r.created_at else "",
        }
        for r in reports
    ]
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


    allowed_fields = ["title", "description", "attachment", "category"]
    
    if current_user.role in ("manager", "analyst"):
        allowed_fields.append("priority")
        allowed_fields.append("status")
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




