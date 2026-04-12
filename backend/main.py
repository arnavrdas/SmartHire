from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers import auth, jobs, applications, interview, admin
from db.session import engine
from db import models

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="SmartHire API", version="3.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router,         prefix="/auth",         tags=["Auth"])
app.include_router(jobs.router,         prefix="/jobs",         tags=["Jobs"])
app.include_router(applications.router, prefix="/applications", tags=["Applications"])
app.include_router(interview.router,    prefix="/interview",    tags=["Interview"])
app.include_router(admin.router,        prefix="/admin",        tags=["Admin"])


@app.get("/")
def root():
    return {"message": "SmartHire API v3 is running"}