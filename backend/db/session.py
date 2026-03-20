"""
db/session.py
-------------
Creates the SQLAlchemy engine (the database connection) and
the session factory (used to run queries).

Every router that needs to query the DB calls get_db() as a
FastAPI dependency to get a fresh session for that request.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

from core.config import settings

# The engine is a low-level connection pool to PostgreSQL.
# connect_args is only needed for SQLite; for Postgres it's empty.
engine = create_engine(settings.DATABASE_URL)

# SessionLocal is a factory: calling SessionLocal() gives you a new session.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base is the parent class all models inherit from.
class Base(DeclarativeBase):
    pass


def get_db():
    """
    FastAPI dependency.  Usage in a router:

        @router.get("/example")
        def example(db: Session = Depends(get_db)):
            ...

    The 'yield' makes this a context manager: the session is
    opened before the route runs and closed after it returns.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
