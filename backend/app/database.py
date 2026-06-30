from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode

from app.config import settings


def _normalize_db_url(url: str):
    """
    Returns (sqlalchemy_url, connect_args) for either SQLite or Postgres.

    External Postgres providers (Neon, Supabase, Railway) hand out libpq URLs like:
        postgresql://user:pass@host/db?sslmode=require&channel_binding=require
    The asyncpg driver does not understand those libpq query params, so we strip
    them and enable TLS through connect_args instead.
    """
    if url.startswith("sqlite"):
        return url, {"check_same_thread": False}

    # Force the async driver
    if url.startswith("postgres://"):
        url = "postgresql+asyncpg://" + url[len("postgres://"):]
    elif url.startswith("postgresql://"):
        url = "postgresql+asyncpg://" + url[len("postgresql://"):]

    parts = urlsplit(url)
    query = dict(parse_qsl(parts.query))

    # libpq-only params asyncpg can't parse
    libpq_only = {"sslmode", "channel_binding", "sslrootcert", "options", "ssl"}
    requires_ssl = query.get("sslmode", "require") not in ("disable", "allow")
    clean_query = {k: v for k, v in query.items() if k not in libpq_only}

    url = urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(clean_query), parts.fragment))

    connect_args = {"ssl": True} if requires_ssl else {}
    return url, connect_args


DATABASE_URL, connect_args = _normalize_db_url(settings.DATABASE_URL)

engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    future=True,
    connect_args=connect_args,
    pool_pre_ping=True,  # survives idle/serverless DBs (e.g. Neon scale-to-zero)
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
)

Base = declarative_base()

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
