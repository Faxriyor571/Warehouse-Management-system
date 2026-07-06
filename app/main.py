"""FastAPI application entry point for the Warehouse Management System.

Run locally with::

    uvicorn app.main:app --reload
"""
from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app import __version__
from app.config import settings
from app.routers.api import api_router
from app.utils.exceptions import AppError

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("wms")

API_PREFIX = "/api/v1"


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Application lifespan: initialise the database on startup."""
    logger.info("Ilova ishga tushmoqda: %s v%s", settings.app_name, __version__)
    try:
        # Imported lazily so the module (and tests) load even if the DB is down.
        from app.db_init import init_db

        init_db()
    except Exception:  # pragma: no cover - defensive startup guard
        logger.exception(
            "Ma'lumotlar bazasini boshlashda xatolik. "
            "PostgreSQL ishga tushganini va .env sozlamalarini tekshiring."
        )
    yield
    logger.info("Ilova to'xtatilmoqda")


app = FastAPI(
    title=settings.app_name,
    description=(
        "Kichik korxonalar uchun ombor boshqaruv tizimi backend API. "
        "Mahsulot kirim/chiqimi, qarz nazorati, hisobotlar va rol asosidagi "
        "ruxsatlar (RBAC)."
    ),
    version=__version__,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Exception handlers
# ---------------------------------------------------------------------------
@app.exception_handler(AppError)
async def app_error_handler(_: Request, exc: AppError) -> JSONResponse:
    """Translate domain errors into JSON responses with the right status code."""
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})


@app.exception_handler(RequestValidationError)
async def validation_error_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    """Return a 422 with a compact list of validation errors.

    ``exc.errors()`` may contain non-JSON-serializable values in ``ctx`` — e.g.
    the raw exception object when a schema validator raises ``ValueError`` — so
    it is passed through ``jsonable_encoder`` (the same approach FastAPI's own
    default handler uses) before serialization. Without this, such a validation
    error would crash this handler and surface as a 500 instead of a 422. The
    response shape is unchanged.
    """
    return JSONResponse(
        status_code=422,
        content={"detail": "Ma'lumotlar noto'g'ri", "errors": jsonable_encoder(exc.errors())},
    )


@app.exception_handler(Exception)
async def unhandled_error_handler(_: Request, exc: Exception) -> JSONResponse:
    """Catch-all handler that avoids leaking internal details in production."""
    logger.exception("Kutilmagan xatolik: %s", exc)
    message = "Ichki server xatosi"
    if settings.debug:
        message = f"{type(exc).__name__}: {exc}"
    return JSONResponse(status_code=500, content={"detail": message})


# ---------------------------------------------------------------------------
# Static files (uploaded images + app assets)
# ---------------------------------------------------------------------------
app.mount(
    "/uploads",
    StaticFiles(directory=str(settings.upload_path)),
    name="uploads",
)
_static_dir = settings.base_dir / "app" / "static"
_static_dir.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(_static_dir)), name="static")


# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
app.include_router(api_router, prefix=API_PREFIX)


# ---------------------------------------------------------------------------
# Root & health
# ---------------------------------------------------------------------------
@app.get("/", tags=["Meta"], summary="Ilova haqida")
def root() -> dict[str, str]:
    return {
        "app": settings.app_name,
        "version": __version__,
        "docs": "/docs",
        "api": API_PREFIX,
        "status": "ok",
    }


@app.get("/health", tags=["Meta"], summary="Sog'lomlik tekshiruvi")
def health() -> dict[str, str]:
    """Lightweight health check that also verifies DB connectivity."""
    from sqlalchemy import text

    from app.database import engine

    db_status = "ok"
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception:  # pragma: no cover
        db_status = "unavailable"
    return {"status": "ok", "database": db_status, "version": __version__}
