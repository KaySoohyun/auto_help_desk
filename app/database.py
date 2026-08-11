from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings

# Opciones de DSN que el transaction pooler de Supabase agrega (pgbouncer=true,
# connection_limit) y que psycopg2/libpq rechaza como opciones desconocidas.
_UNSUPPORTED_DSN_OPTIONS = {"pgbouncer", "connection_limit"}


def _build_database_url() -> str:
    """URL de base de datos compatible con el driver activo.

    psycopg2 no acepta las opciones `pgbouncer`/`connection_limit` que Supabase
    añade a la URL del transaction pooler, y falla con `invalid dsn`. Se eliminan
    antes de construir el engine; no son necesarias para clientes libpq.
    """
    url = make_url(settings.database_url)
    if url.drivername.startswith("postgresql") and url.query:
        url = url.set(
            query={
                key: value
                for key, value in url.query.items()
                if key not in _UNSUPPORTED_DSN_OPTIONS
            }
        )
    return url.render_as_string(hide_password=False)


database_url = _build_database_url()
connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}

engine = create_engine(database_url, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
