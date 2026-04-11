from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base

if TYPE_CHECKING:
    from src.models.product import SKU


class ReservationStatus(str, enum.Enum):
    active = "active"
    converted = "converted"
    expired = "expired"
    released = "released"


class StockLevel(Base):
    __tablename__ = "stock_levels"
    __table_args__ = (
        CheckConstraint("total >= 0", name="ck_stock_levels_total_non_negative"),
        CheckConstraint("reserved >= 0", name="ck_stock_levels_reserved_non_negative"),
        CheckConstraint("reserved <= total", name="ck_stock_levels_reserved_lte_total"),
    )

    sku_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("skus.id"), primary_key=True
    )
    total: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    reserved: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    sku: Mapped[SKU] = relationship("SKU", back_populates="stock_level")

    @property
    def available(self) -> int:
        return self.total - self.reserved


class StockReservation(Base):
    __tablename__ = "stock_reservations"
    __table_args__ = (
        Index(
            "idx_stock_reservations_expires",
            "expires_at",
            postgresql_where="status = 'active'",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    sku_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("skus.id"), nullable=False
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[ReservationStatus] = mapped_column(
        Enum(ReservationStatus, name="stock_reservation_status"),
        nullable=False,
        default=ReservationStatus.active,
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
