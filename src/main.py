import uuid
from collections.abc import AsyncGenerator, Awaitable, Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator

from src.api.health import router as health_router
from src.api.router import router as api_router
from src.config import get_settings
from src.logging_config import configure_logging


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    configure_logging()
    yield


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="Inventory Service",
        version=settings.service_version,
        lifespan=lifespan,
    )

    # CORS — allow browser clients (storefront, admin) in development
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Prometheus metrics
    Instrumentator().instrument(app).expose(app, endpoint="/metrics")

    # X-Request-ID middleware
    @app.middleware("http")
    async def request_id_middleware(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        request_id = request.headers.get("x-request-id", str(uuid.uuid4()))
        response = await call_next(request)
        response.headers["x-request-id"] = request_id
        return response

    app.include_router(health_router)
    app.include_router(api_router, prefix="/api/v1")

    return app


app = create_app()

