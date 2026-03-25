from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app import models
from ..schemas.department_schemas import DepartmentCreate, DepartmentResponse

router = APIRouter(prefix="/departments", tags=["Departments"])




def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/", response_model=DepartmentResponse)
def create_department(dept: DepartmentCreate, db: Session = Depends(get_db)):
    existing = db.query(models.Department).filter(models.Department.name == dept.name).first()

    if existing:
        raise HTTPException(status_code=400, detail="Department already exists")

    new_dept = models.Department(name=dept.name)

    db.add(new_dept)
    db.commit()
    db.refresh(new_dept)

    return new_dept

@router.get("/", response_model=list[DepartmentResponse])
def get_departments(db: Session = Depends(get_db)):
    return db.query(models.Department).all()

@router.get("/{department_id}", response_model=DepartmentResponse)
def get_department(department_id: int, db: Session = Depends(get_db)):
    dept = db.query(models.Department).filter(models.Department.id == department_id).first()

    if not dept:
        raise HTTPException(status_code=404, detail="Department not found")

    return dept

@router.put("/{department_id}", response_model=DepartmentResponse)
def update_department(department_id: int, dept: DepartmentCreate, db: Session = Depends(get_db)):
    department = db.query(models.Department).filter(models.Department.id == department_id).first()

    if not department:
        raise HTTPException(status_code=404, detail="Department not found")

    department.name = dept.name

    db.commit()
    db.refresh(department)

    return department

@router.delete("/{department_id}")
def delete_department(department_id: int, db: Session = Depends(get_db)):
    department = db.query(models.Department).filter(models.Department.id == department_id).first()

    if not department:
        raise HTTPException(status_code=404, detail="Department not found")

    db.delete(department)
    db.commit()

    return {"message": "Department deleted"}