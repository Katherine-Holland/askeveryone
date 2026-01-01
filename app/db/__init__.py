from app.db.session import _engine
from app.db.models import Base

def init_db():
    if _engine is None:
        return
    Base.metadata.create_all(bind=_engine)
