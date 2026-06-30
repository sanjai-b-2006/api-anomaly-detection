import logging
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncEngine
from sqlalchemy.orm import declarative_base
from sqlalchemy.pool import StaticPool
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode

from app.config import settings

logger = logging.getLogger("uvicorn.error")


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


def _safe(url: str) -> str:
    """Mask the password before logging a connection URL."""
    try:
        parts = urlsplit(url)
        if parts.password:
            netloc = parts.netloc.replace(f":{parts.password}@", ":****@")
            return urlunsplit((parts.scheme, netloc, parts.path, "", ""))
    except Exception:
        pass
    return url


DATABASE_URL, _connect_args = _normalize_db_url(settings.DATABASE_URL)

engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    future=True,
    connect_args=_connect_args,
    pool_pre_ping=True,  # survives idle/serverless DBs (e.g. Neon scale-to-zero)
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
)

Base = declarative_base()

# Reflects which backend is actually serving requests (updated by init_db).
DB_STATUS = {"url": _safe(DATABASE_URL), "in_memory_fallback": False}


async def _create_all(eng: AsyncEngine):
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def init_db() -> AsyncEngine:
    """
    Initialize the database and return the engine that is actually active.

    If the configured database can't be reached (wrong URL, Neon down, network
    error), fall back to an in-memory SQLite store so the app keeps running for
    the lifetime of the process. In-memory data is NOT persisted across restarts.
    """
    global engine
    try:
        await _create_all(engine)
        logger.info(f"[db] connected to {DB_STATUS['url']}")
        return engine
    except Exception as e:
        logger.warning(
            f"[db] configured database unavailable ({type(e).__name__}: {e}); "
            f"falling back to IN-MEMORY SQLite — data will NOT persist this session"
        )
        try:
            await engine.dispose()
        except Exception:
            pass

        # StaticPool keeps a single shared connection so the in-memory DB
        # survives across sessions for the whole process lifetime.
        engine = create_async_engine(
            "sqlite+aiosqlite://",
            echo=False,
            future=True,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        AsyncSessionLocal.configure(bind=engine)  # rebind existing sessionmaker in place
        DB_STATUS["url"] = "in-memory sqlite"
        DB_STATUS["in_memory_fallback"] = True
        await _create_all(engine)
        logger.info("[db] running on in-memory SQLite fallback")
        return engine


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
