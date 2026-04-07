from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from typing import List

from .dependencies import get_db
from ..models.user_model import User
from ..schemas.auth_schemas import LoginResponse
from ..schemas.user_schemas import UserResponse
from ..utils.security import verify_password, create_access_token, decode_access_token

router = APIRouter(
    prefix="/auth",
    tags=["Auth"]
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


# ------------------------------------------------------------------ #
#  POST /auth/login                                                   #
# ------------------------------------------------------------------ #
@router.post("/login", response_model=LoginResponse)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    # OAuth2PasswordRequestForm usa "username"; mapeamos para email
    user = db.query(User).filter(User.email == form_data.username).first()

    # Sempre verificamos senha mesmo se user não existe (evita timing attack)
    if not user or not verify_password(form_data.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(data={"sub": str(user.id), "role": user.role})
    return LoginResponse(access_token=access_token)


# ------------------------------------------------------------------ #
#  Dependência reutilizável: get_current_user                        #
# ------------------------------------------------------------------ #
def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception

    user_id: str = payload.get("sub")
    if user_id is None:
        raise credentials_exception

    # Valida que sub é inteiro válido
    try:
        user_id_int = int(user_id)
    except (ValueError, TypeError):
        raise credentials_exception

    user = db.get(User, user_id_int)
    if user is None:
        raise credentials_exception

    return user


# ------------------------------------------------------------------ #
#  GET /auth/me                                                       #
# ------------------------------------------------------------------ #
@router.get("/me", response_model=UserResponse)
def me(current_user: User = Depends(get_current_user)):
    return current_user


# ------------------------------------------------------------------ #
#  Dependência de controle de acesso por role                        #
# ------------------------------------------------------------------ #
def require_roles(allowed_roles: List[str]):
    def role_checker(current_user: User = Depends(get_current_user)):
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions"
            )
        return current_user
    return role_checker