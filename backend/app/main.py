from fastapi import FastAPI
from .database import Base, engine
from .models import user_model, department_model, reports_model
# importa os routers
from .routers import users,auth,report,department

app = FastAPI()

# cria tabelas
Base.metadata.create_all(bind=engine)

# registra rotas
app.include_router(users.router)
app.include_router(auth.router)         
app.include_router(report.router)         
app.include_router(department.router)
@app.get("/")
def home():
    return {"message": "API is running"}