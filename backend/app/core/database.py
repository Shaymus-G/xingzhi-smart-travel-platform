from typing import Generator
from urllib.parse import quote_plus
from sqlalchemy import create_engine
from sqlalchemy.orm import (
    DeclarativeBase,
    sessionmaker,
    Session,
)
from app.core.config import settings

DATABASE_URL = (
    f"mysql+pymysql://"
    f"{quote_plus(settings.MYSQL_USER)}:"
    f"{quote_plus(settings.MYSQL_PASSWORD)}@"
    f"{settings.MYSQL_HOST}:"
    f"{settings.MYSQL_PORT}/"
    f"{settings.MYSQL_DATABASE}"
    "?charset=utf8mb4"
)

# TiDB Cloud SSL 连接配置
_connect_args = {}
if "tidbcloud" in settings.MYSQL_HOST:
    _connect_args = {"ssl": {"fake_flag": True}}

engine = create_engine(
    DATABASE_URL,
    echo=settings.DEBUG,
    pool_pre_ping=True,
    connect_args=_connect_args,
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
)

class Base(DeclarativeBase):
    """所有 ORM Model 的基类"""
    pass

def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()