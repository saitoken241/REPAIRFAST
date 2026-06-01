from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import SessionLocal
from ..models.reports_model import Report, ReportHistory, ActionPlan
from ..models.user_model import User
from ..schemas.report_schemas import UserCreateReport, ReportResponse, UserUpdateReport, ReportCriticoResponse, ReportHistoryCreate, ReportHistoryResponse, ActionPlanCreate, ActionPlanUpdate
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

@router.post("/")
def create_report(request: UserCreateReport, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    print(f"[create_report] department_id recebido: {request.department_id}, user dept: {current_user.department_id}")
    kwargs = dict(
        title=request.title,
        description=request.description,
        attachment=request.attachment,
        category=request.category,
        user_id=current_user.id,
        department_id=request.department_id if request.department_id else current_user.department_id
    )
    # occurrence_type só existe se estiver no modelo
    if request.occurrence_type and hasattr(Report, 'occurrence_type'):
        kwargs['occurrence_type'] = request.occurrence_type

    new_report = Report(**kwargs)
    db.add(new_report)
    db.commit()

    # Recarregar com relações para serialização
    new_report = db.query(Report).options(
        joinedload(Report.department),
        joinedload(Report.user)
    ).filter(Report.id == new_report.id).first()

    return _serialize_report(new_report)

def _serialize_report(r):
    return {
        "id":               r.id,
        "title":            r.title,
        "description":      r.description,
        "attachment":       r.attachment,
        "category":         r.category,
        "priority":         r.priority,
        "status":           r.status,
        "occurrence_type":  getattr(r, "occurrence_type", None),
        "department_id":    r.department_id,
        "department_name":  r.department.name if r.department else None,
        "assigned_to":      getattr(r, "assigned_to", None),
        "assigned_to_name": r.assignee.name if getattr(r, "assignee", None) else None,
        "reporter_name":    r.user.name if r.user else None,
        "created_at":       r.created_at.isoformat() if r.created_at else None,
        "updated_at":       r.closed_at.isoformat() if r.closed_at else (r.created_at.isoformat() if r.created_at else None),
    }

@router.get("/me")
def list_my_reports(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Reportes criados pelo próprio usuário logado (analista ou funcionário)."""
    reports = db.query(Report).options(
        joinedload(Report.department),
        joinedload(Report.user),
        joinedload(Report.assignee)
    ).filter(Report.user_id == current_user.id).order_by(Report.created_at.desc()).all()
    return [_serialize_report(r) for r in reports]

@router.get("/")
def list_reports(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role in ("manager", "analyst"):
        reports = db.query(Report).options(
            joinedload(Report.department),
            joinedload(Report.user),
            joinedload(Report.assignee)
        ).filter(Report.department_id == current_user.department_id).order_by(Report.created_at.desc()).all()
    else:
        reports = db.query(Report).options(
            joinedload(Report.department),
            joinedload(Report.user),
            joinedload(Report.assignee)
        ).filter(Report.user_id == current_user.id).order_by(Report.created_at.desc()).all()
    return [_serialize_report(r) for r in reports]
    
@router.get("/me")
def get_my_reports(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Reportes criados pelo usuário logado — independente do role."""
    reports = db.query(Report).options(
        joinedload(Report.department),
        joinedload(Report.user),
        joinedload(Report.assignee)
    ).filter(Report.user_id == current_user.id).order_by(Report.created_at.desc()).all()
    return [_serialize_report(r) for r in reports]

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




@router.get("/department/stats")
def get_department_stats(
    periodo: str = "mensal",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role not in ("manager", "analyst"):
        raise HTTPException(403, "Not authorized")

    from datetime import datetime, timedelta, date
    from sqlalchemy import extract, and_

    dept_id = current_user.department_id
    hoje    = datetime.now()

    # Define o filtro de data baseado no período
    if periodo == "semanal":
        data_inicio = hoje - timedelta(days=7)
    elif periodo == "anual":
        data_inicio = hoje - timedelta(days=365)
    else:  # mensal (padrão)
        data_inicio = hoje - timedelta(days=30)

    def filtro_base():
        return [
            Report.department_id == dept_id,
            Report.created_at >= data_inicio
        ]

    # ── 1. Por status ──
    por_status = {"open": 0, "in_progress": 0, "closed": 0}
    for row in db.query(Report.status, func.count(Report.id)).filter(
        Report.department_id == dept_id
    ).group_by(Report.status).all():
        if row[0] in por_status:
            por_status[row[0]] = row[1]

    # ── 2. Por prioridade ──
    por_prioridade = {"low": 0, "medium": 0, "high": 0}
    for row in db.query(Report.priority, func.count(Report.id)).filter(
        Report.department_id == dept_id
    ).group_by(Report.priority).all():
        if row[0] in por_prioridade:
            por_prioridade[row[0]] = row[1]

    # ── 3. Por tipo de ocorrência ──
    por_tipo = {"failure": 0, "risk": 0, "improvement": 0}
    for row in db.query(Report.occurrence_type, func.count(Report.id)).filter(
        Report.department_id == dept_id
    ).group_by(Report.occurrence_type).all():
        if row[0] in por_tipo:
            por_tipo[row[0]] = row[1]

    # ── 4. Por categoria ──
    cat_rows = db.query(
        Report.category,
        func.count(Report.id).label("total")
    ).filter(
        *filtro_base(),
        Report.category.isnot(None)
    ).group_by(Report.category).order_by(func.count(Report.id).desc()).limit(8).all()
    por_categoria = [{"label": r[0], "total": r[1]} for r in cat_rows]

    # ── 5. Prioridade x Status (matriz para barras agrupadas) ──
    prio_status_rows = db.query(
        Report.priority,
        Report.status,
        func.count(Report.id).label("total")
    ).filter(*filtro_base()).group_by(Report.priority, Report.status).all()

    prio_status = {
        "high":   {"open": 0, "in_progress": 0, "closed": 0},
        "medium": {"open": 0, "in_progress": 0, "closed": 0},
        "low":    {"open": 0, "in_progress": 0, "closed": 0},
    }
    for row in prio_status_rows:
        if row[0] in prio_status and row[1] in prio_status[row[0]]:
            prio_status[row[0]][row[1]] = row[2]

    # ── 6. Aging — faixas de tempo em aberto (só reportes não fechados) ──
    # Aging usa todos os reportes em aberto sem filtro de período
    aging = {"0_7": 0, "7_14": 0, "15_30": 0, "31_60": 0, "60_plus": 0}
    abertos = db.query(Report.created_at).filter(
        Report.department_id == dept_id,
        Report.status != "closed",
        Report.created_at.isnot(None)
    ).all()
    for (criado_em,) in abertos:
        dias = (hoje - criado_em).days
        if dias <= 7:
            aging["0_7"] += 1
        elif dias <= 14:
            aging["7_14"] += 1
        elif dias <= 30:
            aging["15_30"] += 1
        elif dias <= 60:
            aging["31_60"] += 1
        else:
            aging["60_plus"] += 1

    # ── 7. Por responsável ──
    resp_rows = db.query(
        User.name,
        func.count(Report.id).label("total"),
        func.sum(case((Report.status == "open", 1), else_=0)).label("aberto"),
        func.sum(case((Report.status == "in_progress", 1), else_=0)).label("andamento"),
        func.sum(case((Report.status == "closed", 1), else_=0)).label("resolvido"),
    ).join(User, Report.assigned_to == User.id).filter(
        *filtro_base()
    ).group_by(User.id, User.name).order_by(func.count(Report.id).desc()).limit(8).all()
    por_responsavel = [
        {"nome": r[0], "total": r[1], "aberto": r[2], "andamento": r[3], "resolvido": r[4]}
        for r in resp_rows
    ]

    # ── 8. Volume — abertos e fechados por período ──
    meses, abertos_m, fechados_m = [], [], []
    if periodo == "semanal":
        # Últimos 7 dias, um ponto por dia
        for i in range(6, -1, -1):
            dia = hoje - timedelta(days=i)
            ab = db.query(func.count(Report.id)).filter(
                Report.department_id == dept_id,
                extract("day",   Report.created_at) == dia.day,
                extract("month", Report.created_at) == dia.month,
                extract("year",  Report.created_at) == dia.year,
            ).scalar() or 0
            fe = db.query(func.count(Report.id)).filter(
                Report.department_id == dept_id,
                Report.status == "closed",
                extract("day",   Report.created_at) == dia.day,
                extract("month", Report.created_at) == dia.month,
                extract("year",  Report.created_at) == dia.year,
            ).scalar() or 0
            meses.append(dia.strftime("%d/%m"))
            abertos_m.append(ab)
            fechados_m.append(fe)
    elif periodo == "anual":
        # Últimos 12 meses, um ponto por mês
        for i in range(11, -1, -1):
            mes = (hoje.month - i - 1) % 12 + 1
            ano = hoje.year + ((hoje.month - i - 1) // 12)
            ab = db.query(func.count(Report.id)).filter(
                Report.department_id == dept_id,
                extract("month", Report.created_at) == mes,
                extract("year",  Report.created_at) == ano,
            ).scalar() or 0
            fe = db.query(func.count(Report.id)).filter(
                Report.department_id == dept_id,
                Report.status == "closed",
                extract("month", Report.created_at) == mes,
                extract("year",  Report.created_at) == ano,
            ).scalar() or 0
            meses.append(f"{mes:02d}/{str(ano)[2:]}")
            abertos_m.append(ab)
            fechados_m.append(fe)
    else:
        # Últimos 6 meses, um ponto por mês
        for i in range(5, -1, -1):
            mes = (hoje.month - i - 1) % 12 + 1
            ano = hoje.year + ((hoje.month - i - 1) // 12)
            ab = db.query(func.count(Report.id)).filter(
                Report.department_id == dept_id,
                extract("month", Report.created_at) == mes,
                extract("year",  Report.created_at) == ano,
            ).scalar() or 0
            fe = db.query(func.count(Report.id)).filter(
                Report.department_id == dept_id,
                Report.status == "closed",
                extract("month", Report.created_at) == mes,
                extract("year",  Report.created_at) == ano,
            ).scalar() or 0
            meses.append(f"{mes:02d}/{str(ano)[2:]}")
            abertos_m.append(ab)
            fechados_m.append(fe)

    return {
        "por_status":      por_status,
        "por_prioridade":  por_prioridade,
        "por_tipo":        por_tipo,
        "por_categoria":   por_categoria,
        "prio_status":     prio_status,
        "aging":           aging,
        "por_responsavel": por_responsavel,
        "mensal": {
            "labels":   meses,
            "abertos":  abertos_m,
            "fechados": fechados_m,
        },
    }


@router.get("/company/resume")
def get_company_resume(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Resumo de todos os reportes da empresa — apenas gestor."""
    if current_user.role != "manager":
        raise HTTPException(status_code=403, detail="Not authorized")
    total     = db.query(func.count(Report.id)).scalar() or 0
    aberto    = db.query(func.count(Report.id)).filter(Report.status == "open").scalar() or 0
    andamento = db.query(func.count(Report.id)).filter(Report.status == "in_progress").scalar() or 0
    resolvido = db.query(func.count(Report.id)).filter(Report.status == "closed").scalar() or 0
    return {"total": total, "aberto": aberto, "andamento": andamento, "resolvido": resolvido}


@router.get("/company/reports")
def get_company_reports(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Todos os reportes da empresa — apenas gestor."""
    if current_user.role != "manager":
        raise HTTPException(status_code=403, detail="Not authorized")
    reports = db.query(Report).options(
        joinedload(Report.department),
        joinedload(Report.user),
        joinedload(Report.assignee)
    ).order_by(Report.created_at.desc()).all()
    return [_serialize_report(r) for r in reports]


@router.get("/company/stats")
def get_company_stats(
    periodo: str = "mensal",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Estatísticas de toda a empresa — apenas gestor."""
    if current_user.role != "manager":
        raise HTTPException(403, "Not authorized")

    from datetime import datetime, timedelta
    from sqlalchemy import extract

    hoje = datetime.now()

    if periodo == "semanal":
        data_inicio = hoje - timedelta(days=7)
    elif periodo == "anual":
        data_inicio = hoje - timedelta(days=365)
    else:
        data_inicio = hoje - timedelta(days=30)

    def filtro_periodo():
        return [Report.created_at >= data_inicio]

    # 1. Por status
    por_status = {"open": 0, "in_progress": 0, "closed": 0}
    for row in db.query(Report.status, func.count(Report.id)).filter(
        *filtro_periodo()
    ).group_by(Report.status).all():
        if row[0] in por_status:
            por_status[row[0]] = row[1]

    # 2. Por prioridade
    por_prioridade = {"low": 0, "medium": 0, "high": 0}
    for row in db.query(Report.priority, func.count(Report.id)).filter(
        *filtro_periodo()
    ).group_by(Report.priority).all():
        if row[0] in por_prioridade:
            por_prioridade[row[0]] = row[1]

    # 3. Por tipo
    por_tipo = {"failure": 0, "risk": 0, "improvement": 0}
    for row in db.query(Report.occurrence_type, func.count(Report.id)).filter(
        *filtro_periodo()
    ).group_by(Report.occurrence_type).all():
        if row[0] in por_tipo:
            por_tipo[row[0]] = row[1]

    # 4. Por categoria
    cat_rows = db.query(
        Report.category, func.count(Report.id).label("total")
    ).filter(*filtro_periodo(), Report.category.isnot(None)
    ).group_by(Report.category).order_by(func.count(Report.id).desc()).limit(8).all()
    por_categoria = [{"label": r[0], "total": r[1]} for r in cat_rows]

    # 5. Prioridade x Status
    prio_status = {
        "high":   {"open": 0, "in_progress": 0, "closed": 0},
        "medium": {"open": 0, "in_progress": 0, "closed": 0},
        "low":    {"open": 0, "in_progress": 0, "closed": 0},
    }
    for row in db.query(Report.priority, Report.status, func.count(Report.id)).filter(
        *filtro_periodo()
    ).group_by(Report.priority, Report.status).all():
        if row[0] in prio_status and row[1] in prio_status[row[0]]:
            prio_status[row[0]][row[1]] = row[2]

    # 6. Aging — todos em aberto sem filtro de período
    aging = {"0_7": 0, "7_14": 0, "15_30": 0, "31_60": 0, "60_plus": 0}
    for (criado_em,) in db.query(Report.created_at).filter(
        Report.status != "closed", Report.created_at.isnot(None)
    ).all():
        dias = (hoje - criado_em).days
        if dias <= 7:       aging["0_7"]    += 1
        elif dias <= 14:    aging["7_14"]   += 1
        elif dias <= 30:    aging["15_30"]  += 1
        elif dias <= 60:    aging["31_60"]  += 1
        else:               aging["60_plus"]+= 1

    # 7. Por responsável
    resp_rows = db.query(
        User.name,
        func.count(Report.id).label("total"),
        func.sum(case((Report.status == "open", 1), else_=0)).label("aberto"),
        func.sum(case((Report.status == "in_progress", 1), else_=0)).label("andamento"),
        func.sum(case((Report.status == "closed", 1), else_=0)).label("resolvido"),
    ).join(User, Report.assigned_to == User.id).filter(
        *filtro_periodo()
    ).group_by(User.id, User.name).order_by(func.count(Report.id).desc()).limit(8).all()
    por_responsavel = [
        {"nome": r[0], "total": r[1], "aberto": r[2], "andamento": r[3], "resolvido": r[4]}
        for r in resp_rows
    ]

    # 8. Volume mensal
    meses, abertos_m, fechados_m = [], [], []
    if periodo == "semanal":
        for i in range(6, -1, -1):
            dia = hoje - timedelta(days=i)
            ab = db.query(func.count(Report.id)).filter(
                extract("day", Report.created_at) == dia.day,
                extract("month", Report.created_at) == dia.month,
                extract("year", Report.created_at) == dia.year,
            ).scalar() or 0
            fe = db.query(func.count(Report.id)).filter(
                Report.status == "closed",
                extract("day", Report.created_at) == dia.day,
                extract("month", Report.created_at) == dia.month,
                extract("year", Report.created_at) == dia.year,
            ).scalar() or 0
            meses.append(dia.strftime("%d/%m"))
            abertos_m.append(ab); fechados_m.append(fe)
    else:
        n_meses = 12 if periodo == "anual" else 6
        for i in range(n_meses - 1, -1, -1):
            mes = (hoje.month - i - 1) % 12 + 1
            ano = hoje.year + ((hoje.month - i - 1) // 12)
            ab = db.query(func.count(Report.id)).filter(
                extract("month", Report.created_at) == mes,
                extract("year", Report.created_at) == ano,
            ).scalar() or 0
            fe = db.query(func.count(Report.id)).filter(
                Report.status == "closed",
                extract("month", Report.created_at) == mes,
                extract("year", Report.created_at) == ano,
            ).scalar() or 0
            meses.append(f"{mes:02d}/{str(ano)[2:]}")
            abertos_m.append(ab); fechados_m.append(fe)

    # 9. Por setor (exclusivo da visão empresa)
    setor_rows = db.query(
        Department.name, func.count(Report.id).label("total")
    ).join(Department, Report.department_id == Department.id).filter(
        *filtro_periodo()
    ).group_by(Department.id, Department.name).order_by(func.count(Report.id).desc()).all()
    por_setor = [{"label": r[0], "total": r[1]} for r in setor_rows]

    return {
        "por_status": por_status, "por_prioridade": por_prioridade,
        "por_tipo": por_tipo, "por_categoria": por_categoria,
        "prio_status": prio_status, "aging": aging,
        "por_responsavel": por_responsavel, "por_setor": por_setor,
        "mensal": {"labels": meses, "abertos": abertos_m, "fechados": fechados_m},
    }

@router.get("/{report_id}")
def get_report(report_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    report = db.query(Report).options(
        joinedload(Report.department),
        joinedload(Report.user),
        joinedload(Report.assignee)
    ).filter(Report.id == report_id).first()

    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    if current_user.role in ("manager", "analyst"):
        if report.department_id != current_user.department_id:
            raise HTTPException(status_code=403, detail="Not authorized")
    else:
        if report.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized")

    return {
        "id":               report.id,
        "title":            report.title,
        "description":      report.description,
        "attachment":       report.attachment,
        "category":         report.category,
        "priority":         report.priority,
        "status":           report.status,
        "occurrence_type":  getattr(report, "occurrence_type", None),
        "department_id":    report.department_id,
        "department_name":  report.department.name if report.department else None,
        "assigned_to":      report.assigned_to,
        "assigned_to_name": report.assignee.name if getattr(report, "assignee", None) else None,
        "reporter_name":    report.user.name if report.user else None,
        "created_at":       report.created_at.isoformat() if report.created_at else None,
        "updated_at":       report.closed_at.isoformat() if report.closed_at else (report.created_at.isoformat() if report.created_at else None),
    }

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
@router.put("/{report_id}")
def update_report(
    report_id: int,
    report_data: UserUpdateReport,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    report = db.query(Report).options(
        joinedload(Report.department),
        joinedload(Report.user),
        joinedload(Report.assignee)
    ).filter(Report.id == report_id).first()

    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    if current_user.role in ("manager", "analyst"):
        if report.department_id != current_user.department_id:
            raise HTTPException(status_code=403, detail="Not authorized")
    else:
        if report.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized")

    allowed_fields = ["title", "description", "attachment", "category"]
    if current_user.role in ("manager", "analyst"):
        allowed_fields += ["priority", "status", "assigned_to", "occurrence_type"]

    for key, value in report_data.dict(exclude_unset=True).items():
        if key in allowed_fields and hasattr(report, key):
            setattr(report, key, value)

    db.commit()

    # Recarrega com todos os relacionamentos para serializar corretamente
    report = db.query(Report).options(
        joinedload(Report.department),
        joinedload(Report.user),
        joinedload(Report.assignee)
    ).filter(Report.id == report_id).first()

    return _serialize_report(report)

# ── GET /reports/{id}/plan ──
@router.get("/{report_id}/plan")
def get_plan(report_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(404, "Report not found")
    if current_user.role in ("manager", "analyst"):
        if report.department_id != current_user.department_id:
            raise HTTPException(403, "Not authorized")
    else:
        if report.user_id != current_user.id:
            raise HTTPException(403, "Not authorized")

    items = db.query(ActionPlan).options(
        joinedload(ActionPlan.assignee)
    ).filter(ActionPlan.report_id == report_id).order_by(ActionPlan.created_at).all()

    return [{
        "id":            i.id,
        "report_id":     i.report_id,
        "description":   i.description,
        "assigned_to":   i.assigned_to,
        "assignee_name": i.assignee.name if i.assignee else None,
        "due_date":      i.due_date,
        "done":          i.done,
        "created_at":    i.created_at.isoformat(),
        "done_at":       i.done_at.isoformat() if i.done_at else None,
    } for i in items]


# ── POST /reports/{id}/plan ──
@router.post("/{report_id}/plan")
def add_plan_item(report_id: int, data: ActionPlanCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(404, "Report not found")
    if current_user.role not in ("manager", "analyst"):
        raise HTTPException(403, "Not authorized")
    if report.department_id != current_user.department_id:
        raise HTTPException(403, "Not authorized")

    item = ActionPlan(
        report_id=report_id,
        description=data.description,
        assigned_to=data.assigned_to,
        due_date=data.due_date,
    )
    db.add(item); db.commit()
    item = db.query(ActionPlan).options(joinedload(ActionPlan.assignee)).filter(ActionPlan.id == item.id).first()
    return {
        "id":            item.id,
        "report_id":     item.report_id,
        "description":   item.description,
        "assigned_to":   item.assigned_to,
        "assignee_name": item.assignee.name if item.assignee else None,
        "due_date":      item.due_date,
        "done":          item.done,
        "created_at":    item.created_at.isoformat(),
        "done_at":       None,
    }


# ── PUT /reports/{id}/plan/{item_id} ──
@router.put("/{report_id}/plan/{item_id}")
def update_plan_item(report_id: int, item_id: int, data: ActionPlanUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(404, "Report not found")
    if current_user.role not in ("manager", "analyst"):
        raise HTTPException(403, "Not authorized")
    if report.department_id != current_user.department_id:
        raise HTTPException(403, "Not authorized")

    item = db.query(ActionPlan).filter(ActionPlan.id == item_id, ActionPlan.report_id == report_id).first()
    if not item:
        raise HTTPException(404, "Plan item not found")

    from datetime import datetime as dt
    update_data = data.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(item, key, value)

    if update_data.get("done") is True and not item.done_at:
        item.done_at = dt.utcnow()
    elif update_data.get("done") is False:
        item.done_at = None

    db.commit()
    item = db.query(ActionPlan).options(joinedload(ActionPlan.assignee)).filter(ActionPlan.id == item_id).first()
    return {
        "id":            item.id,
        "report_id":     item.report_id,
        "description":   item.description,
        "assigned_to":   item.assigned_to,
        "assignee_name": item.assignee.name if item.assignee else None,
        "due_date":      item.due_date,
        "done":          item.done,
        "created_at":    item.created_at.isoformat(),
        "done_at":       item.done_at.isoformat() if item.done_at else None,
    }


# ── DELETE /reports/{id}/plan/{item_id} ──
@router.delete("/{report_id}/plan/{item_id}")
def delete_plan_item(report_id: int, item_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(404, "Report not found")
    if current_user.role not in ("manager", "analyst"):
        raise HTTPException(403, "Not authorized")
    if report.department_id != current_user.department_id:
        raise HTTPException(403, "Not authorized")

    item = db.query(ActionPlan).filter(ActionPlan.id == item_id, ActionPlan.report_id == report_id).first()
    if not item:
        raise HTTPException(404, "Plan item not found")

    db.delete(item); db.commit()
    return {"detail": "Plan item deleted"}


@router.get("/{report_id}/history", response_model=list[ReportHistoryResponse])
def get_history(report_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    report = db.get(Report, report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    if current_user.role in ("analyst", "manager"):
        if report.department_id != current_user.department_id:
            raise HTTPException(status_code=403, detail="Not authorized")
    else:
        if report.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized")
    entries = (
        db.query(ReportHistory)
        .filter(ReportHistory.report_id == report_id)
        .order_by(ReportHistory.created_at.asc())
        .all()
    )
    result = []
    for e in entries:
        result.append(ReportHistoryResponse(
            id=e.id,
            report_id=e.report_id,
            action=e.action,
            description=e.description,
            comment=e.comment,
            color=e.color,
            created_at=e.created_at,
            user_name=e.user.name if e.user else "Sistema",
        ))
    return result


@router.post("/{report_id}/history", response_model=ReportHistoryResponse)
def add_history(report_id: int, payload: ReportHistoryCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    report = db.get(Report, report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    if current_user.role in ("analyst", "manager"):
        if report.department_id != current_user.department_id:
            raise HTTPException(status_code=403, detail="Not authorized")
    else:
        if report.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized")
    entry = ReportHistory(
        report_id=report_id,
        user_id=current_user.id,
        action=payload.action,
        description=payload.description,
        comment=payload.comment,
        color=payload.color,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return ReportHistoryResponse(
        id=entry.id,
        report_id=entry.report_id,
        action=entry.action,
        description=entry.description,
        comment=entry.comment,
        color=entry.color,
        created_at=entry.created_at,
        user_name=current_user.name,
    )


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