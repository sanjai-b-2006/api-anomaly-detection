from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import asyncio
import os

from app.config import settings
from app.api.routes import api_router
from app.database import init_db

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Connect to the configured DB; falls back to in-memory SQLite if unavailable
    active_engine = await init_db()

    # Start built-in synthetic traffic generator for live demo
    synthetic_task = None
    if settings.ENABLE_SYNTHETIC:
        from app.ingestion.synthetic_runner import run_synthetic_traffic
        synthetic_task = asyncio.create_task(
            run_synthetic_traffic(delay=settings.SYNTHETIC_DELAY)
        )

    yield

    if synthetic_task:
        synthetic_task.cancel()
    await active_engine.dispose()

app = FastAPI(
    title=settings.PROJECT_NAME,
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get(settings.API_V1_STR + "/health")
async def health():
    from app.database import DB_STATUS
    return {
        "status": "ok",
        "database": DB_STATUS["url"],
        "persistent": not DB_STATUS["in_memory_fallback"],
        "llm": "enabled" if (settings.GROQ_API_KEY or settings.OPENROUTER_API_KEY) else "disabled",
    }


# Serve React frontend — must come after API routes
static_dir = os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "dist")
if os.path.isdir(static_dir):
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
