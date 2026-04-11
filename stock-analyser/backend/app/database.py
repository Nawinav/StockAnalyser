from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.config import settings
import os

# In production set DATABASE_URL env var to a PostgreSQL connection string.
# Locally falls back to SQLite.
_db_url = os.environ.get("DATABASE_URL", f"sqlite:///{settings.DB_PATH}")

# Render/Supabase supply postgres:// but SQLAlchemy 2.x needs postgresql://
if _db_url.startswith("postgres://"):
    _db_url = _db_url.replace("postgres://", "postgresql://", 1)

DATABASE_URL = _db_url

_connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(
    DATABASE_URL,
    connect_args=_connect_args,
    echo=settings.DEBUG
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Create all database tables."""
    from app import models  # noqa: F401 — registers models with Base
    Base.metadata.create_all(bind=engine)
