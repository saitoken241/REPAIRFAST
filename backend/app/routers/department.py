from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .dependencies import get_db
from ..models.department_model import Department
from ..models.user_model import User
from ..schemas.department_schemas import DepartmentCreate, DepartmentResponse
from ..routers.auth import require_roles, get_current_user

router = APIRouter(prefix="/departments", tags=["Departments"])


# ------------------------------------------------------------------ #
#  POST / — somente manager cria departamentos                       #
# ------------------------------------------------------------------ #
@router.post("/", response_model=DepartmentResponse)
def create_department(
    dept: DepartmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["manager"]))
):
    existing = db.query(Department).filter(Department.name == dept.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Department already exists")

    new_dept = Department(name=dept.name)
    db.add(new_dept)
    db.commit()
    db.refresh(new_dept)
    return new_dept


# ------------------------------------------------------------------ #
#  GET / — qualquer usuário autenticado pode listar departamentos    #
# ------------------------------------------------------------------ #
@router.get("/", response_model=list[DepartmentResponse])
def get_departments(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)   # requer autenticação
):
    return db.query(Department).all()


# ------------------------------------------------------------------ #
#  GET /{id} — manager e analyst podem consultar                     #
# ------------------------------------------------------------------ #
@router.get("/{department_id}", response_model=DepartmentResponse)
def get_department(
    department_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["manager", "analyst"]))
):
    dept = db.get(Department, department_id)
    if not dept:
        raise HTTPException(status_code=404, detail="Department not found")
    return dept


# ------------------------------------------------------------------ #
#  PUT /{id} — somente manager atualiza                              #
# ------------------------------------------------------------------ #
@router.put("/{department_id}", response_model=DepartmentResponse)
def update_department(
    department_id: int,
    dept: DepartmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["manager"]))
):
    department = db.get(Department, department_id)
    if not department:
        raise HTTPException(status_code=404, detail="Department not found")

    department.name = dept.name
    db.commit()
    db.refresh(department)
    return department


# ------------------------------------------------------------------ #
#  DELETE /{id} — somente manager remove                             #
# ------------------------------------------------------------------ #
@router.delete("/{department_id}")
def delete_department(
    department_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["manager"]))
):
    department = db.get(Department, department_id)
    if not department:
        raise HTTPException(status_code=404, detail="Department not found")

    db.delete(department)
    db.commit()
    return {"message": "Department deleted"}