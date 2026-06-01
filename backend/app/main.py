from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .database import Base, engine
from .models import user_model, department_model, reports_model
# importa os routers
from .routers import users, auth, report, department

app = FastAPI()

# CORS — permite que o frontend (localhost:3000) acesse a API
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5500",
        "http://127.0.0.1:5500",
        "http://localhost:8080",
        "http://127.0.0.1:8080",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
