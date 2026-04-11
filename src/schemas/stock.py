import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class StockLevelSchema(BaseModel):
    sku_id: uuid.UUID
    available: int
    reserved: int
    total: int

    model_config = {"from_attributes": True}


class ReserveLineRequest(BaseModel):
    sku_id: uuid.UUID
    quantity: int = Field(ge=1)


class ReserveStockRequest(BaseModel):
    order_id: uuid.UUID
    lines: list[ReserveLineRequest] = Field(min_length=1)


class ReserveStockResponse(BaseModel):
    reservation_id: uuid.UUID
    expires_at: datetime


class StockConflict(BaseModel):
    sku_id: uuid.UUID
    requested: int
    available: int


class StockConflictError(BaseModel):
    code: str = "STOCK_CONFLICT"
    message: str
    conflicts: list[StockConflict]


class DeductStockRequest(BaseModel):
    reservation_id: uuid.UUID


class ErrorResponse(BaseModel):
    code: str
    message: str
