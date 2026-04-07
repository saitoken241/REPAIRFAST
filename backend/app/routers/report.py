from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, case

from .dependencies import get_db
from ..models.reports_model import Report
from ..models.user_model import User
from ..schemas.report_schemas import (
    UserCreateReport,
    ReportResponse,
    UserUpdateReport,
    ReportCriticoResponse,
)
from ..routers.auth import get_current_user, require_roles

router = APIRouter(
    prefix="/reports",
    tags=["Report"]
)

# Roles com acesso gerencial
MANAGER_ROLES = ("manager", "analyst")


def _assert_department_access(report: Report, current_user: User) -> None:
    """Garante que manager/analyst só acessa reports do próprio departamento."""
    if current_user.role in MANAGER_ROLES:
        if report.department_id != current_user.department_id:
            raise HTTPException(status_code=403, detail="Not authorized")
    else:
        if report.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized")


# ------------------------------------------------------------------ #
#  ROTAS ESTÁTICAS — devem vir ANTES de /{report_id}                #
# ------------------------------------------------------------------ #

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

    if current_user.role in MANAGER_ROLES:
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
    current_user: User = Depends(require_roles(["manager", "analyst"]))
):
    result = db.query(
        func.count(Report.id).label("total"),
        func.sum(case((Report.status == "open", 1), else_=0)).label("aberto"),
        func.sum(case((Report.status == "in_progress", 1), else_=0)).label("andamento"),
        func.sum(case((Report.status == "closed", 1), else_=0)).label("resolvido"),
    ).filter(Report.department_id == current_user.department_id).one()

    return {
        "total": result.total or 0,
        "aberto": result.aberto or 0,
        "andamento": result.andamento or 0,
        "resolvido": result.resolvido or 0,
    }


@router.get("/department/critical", response_model=list[ReportCriticoResponse])
def get_critical_reports_by_department(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["manager", "analyst"]))
):
    reports = (
        db.query(Report)
        .options(joinedload(Report.user), joinedload(Report.department))
        .filter(
            Report.department_id == current_user.department_id,
            Report.priority == "high",
            Report.status != "closed",
        )
        .all()
    )

    status_map = {
        "open": "aberto",
        "in_progress": "andamento",
        "closed": "resolvido",
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


# ------------------------------------------------------------------ #
#  ROTAS DINÂMICAS — após as estáticas                               #
# ------------------------------------------------------------------ #

@router.post("/", response_model=ReportResponse)
def create_report(
    request: UserCreateReport,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    new_report = Report(
        title=request.title,
        description=request.description,
        attachment=request.attachment,
        category=request.category,
        user_id=current_user.id,
        department_id=current_user.department_id,
    )
    db.add(new_report)
    db.commit()
    db.refresh(new_report)
    return new_report


@router.get("/", response_model=list[ReportResponse])
def list_reports(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role in MANAGER_ROLES:
        return db.query(Report).filter(
            Report.department_id == current_user.department_id
        ).all()
    return db.query(Report).filter(Report.user_id == current_user.id).all()


@router.get("/{report_id}", response_model=ReportResponse)
def get_report(
    report_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    report = db.get(Report, report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    _assert_department_access(report, current_user)
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

    # Employee só edita o próprio; manager/analyst só editam do departamento
    _assert_department_access(report, current_user)

    allowed_fields = {"title", "description", "attachment", "category"}
    if current_user.role in MANAGER_ROLES:
        allowed_fields |= {"priority", "status"}

    for key, value in report_data.dict(exclude_unset=True).items():
        if key in allowed_fields:
            setattr(report, key, value)

    db.commit()
    db.refresh(report)
    return report


@router.delete("/{report_id}")
def delete_report(
    report_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    report = db.get(Report, report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    # Manager → pode deletar apenas do próprio departamento
    # Employee → pode deletar apenas o próprio report
    _assert_department_access(report, current_user)

    db.delete(report)
    db.commit()
    return {"detail": "Report deleted"}