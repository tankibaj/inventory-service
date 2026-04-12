import logging

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from src.config import get_settings

router = APIRouter(tags=["observability"])
logger = logging.getLogger(__name__)
settings = get_settings()

_engine: AsyncEngine | None = None


def get_engine() -> AsyncEngine:
    """Lazy singleton — deferred until first request so tests can inject their engine."""
    from src.database import engine as _db_engine  # noqa: PLC0415

    return _db_engine


@router.get("/health")
async def health() -> JSONResponse:
    return JSONResponse(
        content={
            "status": "ok",
            "service": settings.service_name,
            "version": settings.service_version,
        }
    )


@router.get("/ready")
async def ready() -> JSONResponse:
    try:
        engine = get_engine()
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return JSONResponse(content={"status": "ready"})
    except Exception as exc:
        logger.warning("Readiness check failed", extra={"error": str(exc)})
        return JSONResponse(
            status_code=503,
            content={"status": "not_ready", "reason": "database unavailable"},
        )
