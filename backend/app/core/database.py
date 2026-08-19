from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.core.config import settings

# check_same_thread only matters for SQLite; harmless to set unconditionally
# guarded, but SQLAlchemy only accepts it for the sqlite dialect.
connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}

engine = create_engine(settings.database_url, connect_args=connect_args, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

Base = declarative_base()


def get_db():
    """FastAPI dependency: yields a DB session, guarantees close()."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
