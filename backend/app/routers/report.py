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
from datetime import datetime
import os
import json
import re
import httpx

router = APIRouter(
    prefix="/reports",
    tags=["Report"]
)

def _iso(dt):
    """Serializa datetime UTC adicionando +00:00 para que o JS converta corretamente para horário local."""
    if dt is None:
        return None
    return dt.isoformat() + ("+00:00" if dt.utcoffset() is None else "")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ══════════════════════════════════════════════════════════════════════════════
#  CLASSIFICADOR GROQ — inline, sem dependência de llm_classify / common_config
# ══════════════════════════════════════════════════════════════════════════════

_GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
_GROQ_MODEL   = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")

_SYSTEM_MSG = """Você é um classificador de prioridade de reportes industriais e corporativos (português do Brasil).
Siga as regras de negócio abaixo com rigor:
- Riscos à vida, segurança física, ataques cibernéticos, incêndio, explosão, vazamento de substâncias perigosas NUNCA podem ser prioridade baixa ou média.
- Incidentes que derrubam produção, sistemas críticos ou afetam muitos colaboradores NUNCA podem ser prioridade baixa.
Responda APENAS um objeto JSON com as chaves exatas "priority" (inteiro 1-10) e "priorityLabel" (uma palavra curta: baixa, média ou alta)."""

_INCIDENT_PATTERNS = (
    # Produção / operação
    r"produ[cç][aã]o\s+em\s+baixo",
    r"produ[cç][aã]o\s+(parad|parada|indispon[ií]v|fora|down)",
    r"serv[ií]c(io|os)\s+(principal\s+)?(em\s+baixo|parad|indispon|fora|down)",
    r"todos\s+os\s+clientes",
    r"client(es)?\s+sem\s+acesso",
    r"\bsem\s+acesso\b",
    r"indispon[ií]v(el|íveis)",
    r"parad[ao]\s+total",
    r"perda\s+de\s+(receita|dados)",
    r"\bcr[ií]tic[oa]\b",
    # Segurança física
    r"\bincêndio\b",
    r"\bexplos[aã]o\b",
    r"vazamento\s+de\s+g[aá]s",
    r"vazamento\s+de\s+(produto\s+)?qu[ií]mic",
    r"risco\s+de\s+vida",
    r"risco\s+iminente",
    r"acidente\s+grave",
    r"curto.circu[ií]to",
    r"faí[sç]ca",
    r"odor\s+de\s+queimado",
    r"evacua[cç][aã]o",
    # Segurança cibernética
    r"\bransomware\b",
    r"\bmalware\b",
    r"\bvírus\b",
    r"\bvirus\b",
    r"ataque\s+(cibern[eé]tico|hacker|de\s+rede)",
    r"mensagem\s+de\s+resgate",
    r"arquivos\s+(criptografados|com\s+extens[aã]o\s+desconhecida)",
    r"invas[aã]o\s+de\s+rede",
    r"suspeita\s+de\s+(ataque|hack|invas)",
    r"acesso\s+n[aã]o\s+autorizado",
    r"dados\s+(vazados|expostos|roubados)",
    r"viola[cç][aã]o\s+de\s+seguran",
)

def _build_user_prompt(title: str, description: str, occurrence_type: str, category: str, sector: str) -> str:
    text = f"Title: {title}\nDescription: {description}\nType: {occurrence_type}\nCategory: {category}\nSector: {sector}"
    return f"""Contexto: sistema de reportes de incidentes industriais e corporativos.

Escala (priority):
- 1-3: baixo impacto, rotinas, melhorias cosméticas, sem risco imediato.
- 4-6: impacto moderado, operação parcialmente afetada, prazo normal.
- 7-10: impacto crítico — risco à vida, segurança, ataque cibernético, sistema parado, produção interrompida; resposta urgente.

Regras obrigatórias:
- Risco à vida, acidente, incêndio, explosão, vazamento de gás ou substância perigosa → use 9 ou 10.
- Ataque cibernético, ransomware, malware, vírus, invasão de rede, suspeita de hack → use 9 ou 10.
- Produção/serviço PARADO, INDISPONÍVEL ou sistema crítico fora do ar → use pelo menos 8.
- Vários setores ou colaboradores afetados simultaneamente → use pelo menos 7.
- Não use 1-3 para nenhuma situação com risco de segurança física ou cibernética.

Exemplos:
- "Torneira pingando no banheiro" -> {{"priority": 2, "priorityLabel": "baixa"}}
- "Iluminação insuficiente no corredor" -> {{"priority": 4, "priorityLabel": "média"}}
- "Esteira com trepidação, operação parcial" -> {{"priority": 5, "priorityLabel": "média"}}
- "Servidor principal fora do ar, produção parada" -> {{"priority": 9, "priorityLabel": "alta"}}
- "Suspeita de ransomware, arquivos criptografados, rede ativa" -> {{"priority": 10, "priorityLabel": "alta"}}
- "Vazamento de gás na área de produção, risco de explosão" -> {{"priority": 10, "priorityLabel": "alta"}}
- "Curto-circuito no painel elétrico, risco de incêndio" -> {{"priority": 9, "priorityLabel": "alta"}}

Texto a classificar:
{text!r}

Responda só com JSON neste formato, sem markdown nem texto extra:
{{"priority": <número>, "priorityLabel": "<texto>"}}
"""

def _apply_severity_floor(text: str, priority: int, label: str):
    severe = any(re.search(p, text, re.IGNORECASE) for p in _INCIDENT_PATTERNS)
    if severe and priority < 9:
        return 9, "alta"
    return priority, label

def _classificar_groq(title: str, description: str, occurrence_type: str, category: str, sector: str) -> str:
    """Chama o Groq e retorna 'low', 'medium' ou 'high'. Lança exceção se falhar."""
    if not _GROQ_API_KEY:
        raise ValueError("GROQ_API_KEY não configurada")

    user_prompt = _build_user_prompt(title, description, occurrence_type, category, sector)
    body = {
        "model": _GROQ_MODEL,
        "messages": [
            {"role": "system", "content": _SYSTEM_MSG},
            {"role": "user",   "content": user_prompt},
        ],
        "temperature": 0.15,
    }
    headers = {
        "Authorization": f"Bearer {_GROQ_API_KEY}",
        "Content-Type":  "application/json",
    }
    with httpx.Client(timeout=httpx.Timeout(30.0)) as client:
        r = client.post("https://api.groq.com/openai/v1/chat/completions", json=body, headers=headers)
        r.raise_for_status()

    content = r.json()["choices"][0]["message"]["content"].strip()
    # Remove possíveis blocos markdown
    m = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", content, re.IGNORECASE)
    if m:
        content = m.group(1).strip()

    parsed   = json.loads(content)
    priority = int(parsed["priority"])
    label    = str(parsed["priorityLabel"]).lower().strip()

    # Aplica piso de severidade
    full_text = f"{title} {description} {occurrence_type} {category} {sector}"
    priority, label = _apply_severity_floor(full_text, priority, label)

    # Normaliza label para enum do banco
    label_map = {
        "baixa": "low", "media": "medium", "média": "medium", "alta": "high",
        "low": "low", "medium": "medium", "high": "high",
    }
    return label_map.get(label, "medium")

# ══════════════════════════════════════════════════════════════════════════════

@router.post("/")
def create_report(request: UserCreateReport, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    print(f"[create_report] department_id recebido: {request.department_id}, user dept: {current_user.department_id}")
    kwargs = dict(
        title=request.title,
        description=request.description,
        attachment=request.attachment,
        category=request.category,
        priority="medium",  # default; será sobrescrito pelo Groq
        user_id=current_user.id,
        department_id=request.department_id if request.department_id else current_user.department_id
    )
    if request.occurrence_type and hasattr(Report, 'occurrence_type'):
        kwargs['occurrence_type'] = request.occurrence_type

    new_report = Report(**kwargs)
    db.add(new_report)
    db.commit()

    # ── Classificação automática via Groq ──────────────────────────────────
    try:
        priority_val = _classificar_groq(
            title          = request.title or "",
            description    = request.description or "",
            occurrence_type= request.occurrence_type or "",
            category       = request.category or "",
            sector         = request.sector or "",
        )
        new_report.priority   = priority_val
        new_report.updated_at = datetime.utcnow()
        db.commit()

        label_pt = {"low": "Baixa", "medium": "Média", "high": "Alta"}.get(priority_val, priority_val)
        db.add(ReportHistory(
            report_id   = new_report.id,
            action      = "Classificação automática",
            description = f"Prioridade definida como {label_pt}.",
            color       = "var(--blue)",
        ))
        db.commit()
        print(f"[groq] reporte {new_report.id} classificado como {priority_val}")

    except Exception as groq_err:
        print(f"[groq] falha na classificação do reporte {new_report.id}: {groq_err}")
        db.add(ReportHistory(
            report_id   = new_report.id,
            action      = "Classificação automática",
            description = "Prioridade definida como Média (classificação indisponível).",
            color       = "var(--amber)",
        ))
        db.commit()
    # ──────────────────────────────────────────────────────────────────────

    new_report = db.query(Report).options(
        joinedload(Report.department),
        joinedload(Report.user)
    ).filter(Report.id == new_report.id).first()

    return _serialize_report(new_report)

def _serialize_report(r):
    updated_at_val = (
        getattr(r, "updated_at", None)
        or r.closed_at
        or r.created_at
    )
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
        "created_at":       _iso(r.created_at),
        "updated_at":       _iso(updated_at_val),
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

    if periodo == "semanal":
        data_inicio = hoje - timedelta(days=7)
    elif periodo == "anual":
        data_inicio = hoje - timedelta(days=365)
    else:
        data_inicio = hoje - timedelta(days=30)

    def filtro_base():
        return [
            Report.department_id == dept_id,
            Report.created_at >= data_inicio
        ]

    por_status = {"open": 0, "in_progress": 0, "closed": 0}
    for row in db.query(Report.status, func.count(Report.id)).filter(
        Report.department_id == dept_id
    ).group_by(Report.status).all():
        if row[0] in por_status:
            por_status[row[0]] = row[1]

    por_prioridade = {"low": 0, "medium": 0, "high": 0}
    for row in db.query(Report.priority, func.count(Report.id)).filter(
        Report.department_id == dept_id
    ).group_by(Report.priority).all():
        if row[0] in por_prioridade:
            por_prioridade[row[0]] = row[1]

    por_tipo = {"failure": 0, "risk": 0, "improvement": 0}
    for row in db.query(Report.occurrence_type, func.count(Report.id)).filter(
        Report.department_id == dept_id
    ).group_by(Report.occurrence_type).all():
        if row[0] in por_tipo:
            por_tipo[row[0]] = row[1]

    cat_rows = db.query(
        Report.category,
        func.count(Report.id).label("total")
    ).filter(
        *filtro_base(),
        Report.category.isnot(None)
    ).group_by(Report.category).order_by(func.count(Report.id).desc()).limit(8).all()
    por_categoria = [{"label": r[0], "total": r[1]} for r in cat_rows]

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

    aging = {"0_7": 0, "7_14": 0, "15_30": 0, "31_60": 0, "60_plus": 0}
    abertos = db.query(Report.created_at).filter(
        Report.department_id == dept_id,
        Report.status != "closed",
        Report.created_at.isnot(None)
    ).all()
    for (criado_em,) in abertos:
        dias = (hoje - criado_em).days
        if dias <= 7:       aging["0_7"] += 1
        elif dias <= 14:    aging["7_14"] += 1
        elif dias <= 30:    aging["15_30"] += 1
        elif dias <= 60:    aging["31_60"] += 1
        else:               aging["60_plus"] += 1

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

    meses, abertos_m, fechados_m = [], [], []
    if periodo == "semanal":
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
                Report.closed_at.isnot(None),
                extract("day",   Report.closed_at) == dia.day,
                extract("month", Report.closed_at) == dia.month,
                extract("year",  Report.closed_at) == dia.year,
            ).scalar() or 0
            meses.append(dia.strftime("%d/%m"))
            abertos_m.append(ab)
            fechados_m.append(fe)
    elif periodo == "anual":
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
                Report.closed_at.isnot(None),
                extract("month", Report.closed_at) == mes,
                extract("year",  Report.closed_at) == ano,
            ).scalar() or 0
            meses.append(f"{mes:02d}/{str(ano)[2:]}")
            abertos_m.append(ab)
            fechados_m.append(fe)
    else:
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
                Report.closed_at.isnot(None),
                extract("month", Report.closed_at) == mes,
                extract("year",  Report.closed_at) == ano,
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
    if current_user.role != "manager":
        raise HTTPException(status_code=403, detail="Not authorized")
    total     = db.query(func.count(Report.id)).scalar() or 0
    aberto    = db.query(func.count(Report.id)).filter(Report.status == "open").scalar() or 0
    andamento = db.query(func.count(Report.id)).filter(Report.status == "in_progress").scalar() or 0
    resolvido = db.query(func.count(Report.id)).filter(Report.status == "closed").scalar() or 0
    return {"total": total, "aberto": aberto, "andamento": andamento, "resolvido": resolvido}


@router.get("/company/reports")
def get_company_reports(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
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

    por_status = {"open": 0, "in_progress": 0, "closed": 0}
    for row in db.query(Report.status, func.count(Report.id)).filter(
        *filtro_periodo()
    ).group_by(Report.status).all():
        if row[0] in por_status:
            por_status[row[0]] = row[1]

    por_prioridade = {"low": 0, "medium": 0, "high": 0}
    for row in db.query(Report.priority, func.count(Report.id)).filter(
        *filtro_periodo()
    ).group_by(Report.priority).all():
        if row[0] in por_prioridade:
            por_prioridade[row[0]] = row[1]

    por_tipo = {"failure": 0, "risk": 0, "improvement": 0}
    for row in db.query(Report.occurrence_type, func.count(Report.id)).filter(
        *filtro_periodo()
    ).group_by(Report.occurrence_type).all():
        if row[0] in por_tipo:
            por_tipo[row[0]] = row[1]

    cat_rows = db.query(
        Report.category, func.count(Report.id).label("total")
    ).filter(*filtro_periodo(), Report.category.isnot(None)
    ).group_by(Report.category).order_by(func.count(Report.id).desc()).limit(8).all()
    por_categoria = [{"label": r[0], "total": r[1]} for r in cat_rows]

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
                Report.closed_at.isnot(None),
                extract("day", Report.closed_at) == dia.day,
                extract("month", Report.closed_at) == dia.month,
                extract("year", Report.closed_at) == dia.year,
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
                Report.closed_at.isnot(None),
                extract("month", Report.closed_at) == mes,
                extract("year", Report.closed_at) == ano,
            ).scalar() or 0
            meses.append(f"{mes:02d}/{str(ano)[2:]}")
            abertos_m.append(ab); fechados_m.append(fe)

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
        "created_at":       _iso(report.created_at),
        "updated_at":       _iso(getattr(report,"updated_at",None) or report.closed_at or report.created_at),
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

    old_priority = report.priority
    data_dict    = report_data.dict(exclude_unset=True)
    new_priority = data_dict.get("priority")
    priority_changed = (
        new_priority is not None
        and new_priority != old_priority
        and current_user.role == "analyst"
    )

    for key, value in data_dict.items():
        if key in allowed_fields and hasattr(report, key):
            setattr(report, key, value)

    if data_dict.get("status") == "closed" and not report.closed_at:
        report.closed_at = datetime.utcnow()
    elif data_dict.get("status") in ("open", "in_progress"):
        report.closed_at = None

    report.updated_at = datetime.utcnow()
    db.commit()

    if priority_changed:
        _pt = {"low": "Baixa", "medium": "Média", "high": "Alta"}
        db.add(ReportHistory(
            report_id   = report_id,
            user_id     = current_user.id,
            action      = "Prioridade corrigida",
            description = f"{_pt.get(old_priority, old_priority)} → {_pt.get(new_priority, new_priority)} (corrigido pelo analista)",
            color       = "var(--orange)",
        ))
        db.commit()
        print(f"[priority] reporte {report_id}: {old_priority} → {new_priority} por {current_user.name}")

    report = db.query(Report).options(
        joinedload(Report.department),
        joinedload(Report.user),
        joinedload(Report.assignee)
    ).filter(Report.id == report_id).first()

    return _serialize_report(report)

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
        "created_at":    _iso(i.created_at),
        "done_at":       _iso(i.done_at),
    } for i in items]


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
        "created_at":    _iso(item.created_at),
        "done_at":       None,
    }


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
        "created_at":    _iso(item.created_at),
        "done_at":       _iso(item.done_at),
    }


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

    if current_user.role == "manager":
        if report.department_id != current_user.department_id:
            raise HTTPException(status_code=403, detail="Not authorized")
    else:
        if report.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized")

    db.delete(report)
    db.commit()

    return {"detail": "Report deleted"}