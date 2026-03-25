from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import SessionLocal
from ..models.user_model import User
from ..schemas.user_schemas import UserCreate, UserResponse, UserUpdate
from ..utils.security import hash_password
from ..models.department_model import Department
from ..routers.auth import require_roles

router = APIRouter(
    prefix="/users",
    tags=["Users"]
)
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/", response_model=UserResponse)
def create_user(user: UserCreate, db: Session = Depends(get_db), current_user: User = Depends(require_roles(["manager"]))):
    existing_user = db.query(User).filter(User.email == user.email).first()
    existing_cpf = db.query(User).filter(User.cpf == user.cpf).first()

    if existing_cpf:
        raise HTTPException(status_code=400, detail="CPF already registered")
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    new_user = User(
        name=user.name,
        email=user.email,
        password=hash_password(user.password),
        cpf=user.cpf,
        company = user.company,
        number=user.number,
        department_id = user.department_id,
        role=user.role
    
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return new_user

@router.get("/", response_model=list[UserResponse])
def list_users(db: Session = Depends(get_db),current_user: User = Depends(require_roles(["manager"]))):
    return db.query(User).all()

@router.get("/{user_id}", response_model=UserResponse)
def get_user(user_id: int, db: Session = Depends(get_db), current_user: User = Depends(require_roles(["manager"]))):
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return user



@router.put("/{user_id}", response_model=UserResponse)
def update_user(user_id: int, user_data: UserUpdate, db: Session = Depends(get_db), current_user: User = Depends(require_roles(["manager"]))):
    user = db.get(User, user_id)

    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user_data.department_id is not None:
        department = db.query(Department).filter(Department.id == user_data.department_id).first()
        if not department:
            raise HTTPException(status_code=400, detail="Department not found")
    for key, value in user_data.dict(exclude_unset=True).items():
        if key == "password":
            value = hash_password(value)
        setattr(user, key, value)

    db.commit()
    db.refresh(user)

    return user

@router.delete("/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db), current_user: User = Depends(require_roles(["manager"]))):
    user = db.get(User, user_id)

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    db.delete(user)
    db.commit()

    return {"detail": "User deleted"}