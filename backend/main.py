from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers import auth, jobs, applications
from db.session import engine
from db import models

# Create all database tables on startup
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="SmartHire API", version="1.0.0")

# Allow the React frontend (localhost:5173) to call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers (groups of related routes)
app.include_router(auth.router,         prefix="/auth",         tags=["Auth"])
app.include_router(jobs.router,         prefix="/jobs",         tags=["Jobs"])
app.include_router(applications.router, prefix="/applications", tags=["Applications"])


@app.get("/")
def root():
    return {"message": "SmartHire API is running"}
