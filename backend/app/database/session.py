from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from app.models.orm import Base


def build_engine(url: str):
    kwargs = {}
    if url.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False, "timeout": 30}
    engine = create_engine(url, **kwargs)
    if url.startswith("sqlite"):
        @event.listens_for(engine, "connect")
        def _fk_on(dbapi_conn, _record):
            cur = dbapi_conn.cursor()
            cur.execute("PRAGMA foreign_keys=ON")
            cur.close()
    return engine


def build_session_factory(engine) -> "sessionmaker[Session]":
    return sessionmaker(bind=engine, expire_on_commit=False, class_=Session)


def init_db(engine) -> None:
    """Create tables if they do not exist. For schema changes later, use Alembic (see README)."""
    Base.metadata.create_all(engine)
