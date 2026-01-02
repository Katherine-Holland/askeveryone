from sqlalchemy.orm import declarative_base

# Single shared Base for all models (queries/provider_calls + auth tables)
Base = declarative_base()
