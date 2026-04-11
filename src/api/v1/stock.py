import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, status
from fastapi.responses import Response

from src.dependencies import SessionDep, TenantDep
from src.schemas.stock import (
    DeductStockRequest,
    ErrorResponse,
    ReserveStockRequest,
    ReserveStockResponse,
    StockConflictError,
    StockLevelSchema,
)
from src.services.stock_service import StockService

router = APIRouter(prefix="/stock", tags=["stock"])


@router.get("/{sku_id}", response_model=StockLevelSchema)
async def get_stock_level(
    sku_id: uuid.UUID,
    tenant_id: TenantDep,
    session: SessionDep,
) -> StockLevelSchema:
    service = StockService(session)
    level = await service.get_stock_level(sku_id)
    if level is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "SKU_NOT_FOUND", "message": f"SKU {sku_id} not found"},
        )
    return level


@router.post(
    "/reserve",
    responses={
        200: {"model": ReserveStockResponse},
        409: {"model": StockConflictError},
    },
)
async def reserve_stock(
    tenant_id: TenantDep,
    session: SessionDep,
    body: ReserveStockRequest,
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> ReserveStockResponse | StockConflictError:
    service = StockService(session)
    result = await service.reserve_stock(body)
    if isinstance(result, StockConflictError):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=result.model_dump())
    return result


@router.post("/deduct", status_code=status.HTTP_200_OK)
async def deduct_stock(
    tenant_id: TenantDep,
    session: SessionDep,
    body: DeductStockRequest,
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> Response:
    service = StockService(session)
    success = await service.deduct_stock(body)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "RESERVATION_NOT_FOUND",
                "message": f"Reservation {body.reservation_id} not found or expired",
            },
        )
    return Response(status_code=status.HTTP_200_OK)


@router.post("/reservations/{reservation_id}/release", status_code=status.HTTP_204_NO_CONTENT)
async def release_reservation(
    reservation_id: uuid.UUID,
    tenant_id: TenantDep,
    session: SessionDep,
) -> Response:
    service = StockService(session)
    await service.release_reservation(reservation_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
