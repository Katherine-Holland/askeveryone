from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.config import settings

_engine = None
SessionLocal = None

def init_engine():
    """
    Lazily initialize the SQLAlchemy engine.
    This prevents import-time crashes on Render if env vars aren't ready.
    Forces psycopg (psycopg3) driver via DATABASE_URL scheme: postgresql+psycopg://
    """
    global _engine, SessionLocal

    if _engine is not None:
        return _engine

    if not settings.database_url:
        _engine = None
        SessionLocal = None
        return None

    # IMPORTANT: must be postgresql+psycopg://...
    _engine = create_engine(settings.database_url, pool_pre_ping=True)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine)
    return _engine

def get_session():
    if SessionLocal is None:
        init_engine()
    if SessionLocal is None:
        return None
    return SessionLocal()
