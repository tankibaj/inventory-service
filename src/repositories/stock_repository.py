import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.stock import ReservationStatus, StockLevel, StockReservation


@dataclass
class StockConflict:
    sku_id: uuid.UUID
    requested: int
    available: int


@dataclass
class ReservationResult:
    reservation_id: uuid.UUID
    expires_at: datetime


class StockRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_stock_level(self, sku_id: uuid.UUID) -> StockLevel | None:
        result = await self._session.execute(select(StockLevel).where(StockLevel.sku_id == sku_id))
        return result.scalar_one_or_none()

    async def reserve_stock(
        self,
        order_id: uuid.UUID,
        lines: list[tuple[uuid.UUID, int]],
        expires_at: datetime,
    ) -> ReservationResult | list[StockConflict]:
        """
        Atomically reserve stock for all lines.
        Returns ReservationResult on success, list[StockConflict] on conflict.

        Design: order_id serves as the reservation_id (group key for multi-line reservations).
        Each line creates one StockReservation row. Deduct/release queries by order_id.
        """
        sku_ids = [sku_id for sku_id, _ in lines]
        qty_map = {sku_id: qty for sku_id, qty in lines}

        # Lock rows for update to prevent race conditions
        result = await self._session.execute(
            select(StockLevel).where(StockLevel.sku_id.in_(sku_ids)).with_for_update()
        )
        stock_levels = {sl.sku_id: sl for sl in result.scalars().all()}

        # Check for conflicts before making any changes
        conflicts: list[StockConflict] = []
        for sku_id, qty in lines:
            sl = stock_levels.get(sku_id)
            available = sl.available if sl else 0
            if sl is None or available < qty:
                conflicts.append(
                    StockConflict(
                        sku_id=sku_id,
                        requested=qty,
                        available=available,
                    )
                )

        if conflicts:
            return conflicts

        # All lines pass — create reservation rows and update stock
        for sku_id, qty in lines:
            sl = stock_levels[sku_id]
            sl.reserved += qty

            reservation = StockReservation(
                id=uuid.uuid4(),
                order_id=order_id,  # order_id = reservation group key
                sku_id=sku_id,
                quantity=qty,
                status=ReservationStatus.active,
                expires_at=expires_at,
            )
            self._session.add(reservation)

        await self._session.commit()

        # reservation_id returned to caller == order_id (the group key)
        return ReservationResult(reservation_id=order_id, expires_at=expires_at)

    async def deduct_stock(self, reservation_id: uuid.UUID) -> bool:
        """
        Deduct stock for all active reservation rows associated with reservation_id.
        reservation_id is the order_id used when reserving.
        Returns True on success, False if no active reservation found.
        """
        result = await self._session.execute(
            select(StockReservation)
            .where(
                StockReservation.order_id == reservation_id,
                StockReservation.status == ReservationStatus.active,
            )
            .with_for_update()
        )
        reservations = result.scalars().all()
        if not reservations:
            return False

        sku_ids = [r.sku_id for r in reservations]
        sl_result = await self._session.execute(
            select(StockLevel).where(StockLevel.sku_id.in_(sku_ids)).with_for_update()
        )
        stock_levels = {sl.sku_id: sl for sl in sl_result.scalars().all()}

        for reservation in reservations:
            sl = stock_levels.get(reservation.sku_id)
            if sl:
                sl.total -= reservation.quantity
                sl.reserved -= reservation.quantity
            reservation.status = ReservationStatus.converted

        await self._session.commit()
        return True

    async def release_reservation(self, reservation_id: uuid.UUID) -> None:
        """
        Release active reservation rows. Idempotent — not-found is treated as success.
        reservation_id is the order_id used when reserving.
        """
        result = await self._session.execute(
            select(StockReservation)
            .where(
                StockReservation.order_id == reservation_id,
                StockReservation.status == ReservationStatus.active,
            )
            .with_for_update()
        )
        reservations = result.scalars().all()
        if not reservations:
            return  # Idempotent — already released/converted/expired or not found

        sku_ids = [r.sku_id for r in reservations]
        sl_result = await self._session.execute(
            select(StockLevel).where(StockLevel.sku_id.in_(sku_ids)).with_for_update()
        )
        stock_levels = {sl.sku_id: sl for sl in sl_result.scalars().all()}

        for reservation in reservations:
            sl = stock_levels.get(reservation.sku_id)
            if sl:
                sl.reserved = max(0, sl.reserved - reservation.quantity)
            reservation.status = ReservationStatus.released

        await self._session.commit()

    async def expire_stale_reservations(self) -> int:
        """Mark expired active reservations and release their stock. Returns count."""
        now = datetime.now(timezone.utc)
        result = await self._session.execute(
            select(StockReservation)
            .where(
                StockReservation.status == ReservationStatus.active,
                StockReservation.expires_at <= now,
            )
            .with_for_update(skip_locked=True)
        )
        expired = result.scalars().all()

        sku_ids = [r.sku_id for r in expired]
        if sku_ids:
            sl_result = await self._session.execute(
                select(StockLevel).where(StockLevel.sku_id.in_(sku_ids))
            )
            stock_levels = {sl.sku_id: sl for sl in sl_result.scalars().all()}

            for reservation in expired:
                sl = stock_levels.get(reservation.sku_id)
                if sl:
                    sl.reserved = max(0, sl.reserved - reservation.quantity)
                reservation.status = ReservationStatus.expired

            await self._session.commit()

        return len(expired)
