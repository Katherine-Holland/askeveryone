from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.config import settings

def get_engine():
    if not settings.database_url:
        return None
    return create_engine(settings.database_url, pool_pre_ping=True)

_engine = get_engine()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine) if _engine else None
