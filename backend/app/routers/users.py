from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from  .dependencies import get_db
from ..models.user_model import User
from ..models.department_model import Department
from ..schemas.user_schemas import UserCreate, UserResponse, UserUpdate
from ..utils.security import hash_password
from ..routers.auth import require_roles, get_current_user

router = APIRouter(
    prefix="/users",
    tags=["Users"]
)

# Roles que um manager pode criar — impede escalada de privilégio
ALLOWED_ROLES = {"employee", "analyst"}


# ------------------------------------------------------------------ #
#  POST / — somente manager cria usuários                           #
# ------------------------------------------------------------------ #
@router.post("/", response_model=UserResponse)
def create_user(
    user: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["manager"]))
):
    # Impede que um manager crie outro manager (escalada de privilégio)
    if user.role not in ALLOWED_ROLES:
        raise HTTPException(
            status_code=403,
            detail=f"Cannot assign role '{user.role}'. Allowed: {sorted(ALLOWED_ROLES)}"
        )

    if db.query(User).filter(User.cpf == user.cpf).first():
        raise HTTPException(status_code=400, detail="CPF already registered")
    if db.query(User).filter(User.email == user.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")

    new_user = User(
        name=user.name,
        email=user.email,
        password=hash_password(user.password),
        cpf=user.cpf,
        company=user.company,
        number=user.number,
        department_id=user.department_id,
        role=user.role,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


# ------------------------------------------------------------------ #
#  GET / — manager lista usuários do próprio departamento            #
# ------------------------------------------------------------------ #
@router.get("/", response_model=list[UserResponse])
def list_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["manager"]))
):
    return (
        db.query(User)
        .filter(User.department_id == current_user.department_id)
        .all()
    )


# ------------------------------------------------------------------ #
#  GET /{id} — manager consulta usuário do próprio departamento     #
# ------------------------------------------------------------------ #
@router.get("/{user_id}", response_model=UserResponse)
def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["manager"]))
):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Manager só pode ver usuários do próprio departamento
    if user.department_id != current_user.department_id:
        raise HTTPException(status_code=403, detail="Not authorized")

    return user


# ------------------------------------------------------------------ #
#  PUT /{id} — manager atualiza usuário do próprio departamento     #
# ------------------------------------------------------------------ #
@router.put("/{user_id}", response_model=UserResponse)
def update_user(
    user_id: int,
    user_data: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["manager"]))
):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Manager só pode alterar usuários do próprio departamento
    if user.department_id != current_user.department_id:
        raise HTTPException(status_code=403, detail="Not authorized")

    # Impede escalada de privilégio ao alterar role
    if user_data.role is not None and user_data.role not in ALLOWED_ROLES:
        raise HTTPException(
            status_code=403,
            detail=f"Cannot assign role '{user_data.role}'. Allowed: {sorted(ALLOWED_ROLES)}"
        )

    if user_data.department_id is not None:
        if not db.get(Department, user_data.department_id):
            raise HTTPException(status_code=400, detail="Department not found")

    for key, value in user_data.dict(exclude_unset=True).items():
        if key == "password":
            value = hash_password(value)
        setattr(user, key, value)

    db.commit()
    db.refresh(user)
    return user


# ------------------------------------------------------------------ #
#  DELETE /{id} — manager remove usuário do próprio departamento    #
# ------------------------------------------------------------------ #
@router.delete("/{user_id}")
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["manager"]))
):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Manager só pode deletar usuários do próprio departamento
    if user.department_id != current_user.department_id:
        raise HTTPException(status_code=403, detail="Not authorized")

    db.delete(user)
    db.commit()
    return {"detail": "User deleted"}