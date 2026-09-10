"""Conexão com o SQL Server via SQLAlchemy + pyodbc."""
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import get_settings


class Base(DeclarativeBase):
    pass


def _criar_engine():
    settings = get_settings()
    return create_engine(settings.url_banco, pool_pre_ping=True)


engine = _criar_engine()
SessionLocal = sessionmaker(
    bind=engine, autoflush=False, expire_on_commit=False)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
