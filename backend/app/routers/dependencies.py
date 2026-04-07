
from typing import Generator
from sqlalchemy.orm import Session
from ..database import SessionLocal  # ajuste conforme seu setup


def get_db() -> Generator[Session, None, None]:
    """
    Dependência reutilizável do SQLAlchemy.
    Centralizada aqui para evitar duplicação entre routers.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()