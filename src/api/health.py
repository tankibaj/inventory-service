import logging

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import text

from src.config import get_settings
from src.database import async_session_factory

router = APIRouter(tags=["observability"])
logger = logging.getLogger(__name__)
settings = get_settings()


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
        async with async_session_factory() as session:
            await session.execute(text("SELECT 1"))
        return JSONResponse(content={"status": "ready"})
    except Exception as exc:
        logger.warning("Readiness check failed", extra={"error": str(exc)})
        return JSONResponse(
            status_code=503,
            content={"status": "not_ready", "reason": "database unavailable"},
        )
