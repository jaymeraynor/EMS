
from alembic import context
from sqlalchemy import create_engine

from app.config import resolve_database_url
from app.db import normalize_url
from app.models import Base

config = context.config
target_metadata = Base.metadata


def _url() -> str:
    url = resolve_database_url()
    if not url:
        raise RuntimeError("DATABASE_URL (or POSTGRES_HOST/USER/PASSWORD/DB) is not set")
    return normalize_url(url)


def run_migrations_offline() -> None:
    context.configure(url=_url(), target_metadata=target_metadata, literal_binds=True,
                      compare_type=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    engine = create_engine(_url())
    with engine.connect() as conn:
        context.configure(connection=conn, target_metadata=target_metadata, compare_type=True)
        with context.begin_transaction():
            context.run_migrations()
    engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
