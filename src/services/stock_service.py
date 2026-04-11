import logging
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from src.config import get_settings
from src.repositories.stock_repository import (
    StockRepository,
)
from src.schemas.stock import (
    DeductStockRequest,
    ReserveStockRequest,
    ReserveStockResponse,
    StockConflictError,
    StockLevelSchema,
)
from src.schemas.stock import (
    StockConflict as StockConflictSchema,
)

logger = logging.getLogger(__name__)


class StockService:
    def __init__(self, session: AsyncSession) -> None:
        self._repo = StockRepository(session)
        self._settings = get_settings()

    async def get_stock_level(self, sku_id: uuid.UUID) -> StockLevelSchema | None:
        sl = await self._repo.get_stock_level(sku_id)
        if sl is None:
            return None
        return StockLevelSchema(
            sku_id=sl.sku_id,
            available=sl.available,
            reserved=sl.reserved,
            total=sl.total,
        )

    async def reserve_stock(
        self,
        request: ReserveStockRequest,
    ) -> ReserveStockResponse | StockConflictError:
        expires_at = datetime.now(UTC) + timedelta(
            minutes=self._settings.reservation_ttl_minutes
        )
        lines = [(line.sku_id, line.quantity) for line in request.lines]
        result = await self._repo.reserve_stock(
            order_id=request.order_id,
            lines=lines,
            expires_at=expires_at,
        )

        if isinstance(result, list):
            # Conflicts
            conflicts = [
                StockConflictSchema(
                    sku_id=c.sku_id,
                    requested=c.requested,
                    available=c.available,
                )
                for c in result
            ]
            return StockConflictError(
                code="STOCK_CONFLICT",
                message="Insufficient stock for one or more SKUs",
                conflicts=conflicts,
            )

        return ReserveStockResponse(
            reservation_id=result.reservation_id,
            expires_at=result.expires_at,
        )

    async def deduct_stock(self, request: DeductStockRequest) -> bool:
        """Returns True if deducted, False if reservation not found/expired."""
        return await self._repo.deduct_stock(request.reservation_id)

    async def release_reservation(self, reservation_id: uuid.UUID) -> None:
        await self._repo.release_reservation(reservation_id)

    async def expire_stale_reservations(self) -> None:
        """Background task: expire stale reservations."""
        count = await self._repo.expire_stale_reservations()
        if count > 0:
            logger.info("Expired stale reservations", extra={"count": count})
