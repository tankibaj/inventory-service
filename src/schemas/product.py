import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class SKUSchema(BaseModel):
    id: uuid.UUID
    label: str
    price_minor: int
    stock_level: int

    model_config = {"from_attributes": True}


class ProductSchema(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None = None
    image_url: str | None = None
    skus: list[SKUSchema]
    created_at: datetime

    model_config = {"from_attributes": True}


class PaginationMeta(BaseModel):
    total: int
    page: int
    per_page: int


class ProductPage(BaseModel):
    data: list[ProductSchema]
    meta: PaginationMeta


class CreateSKURequest(BaseModel):
    label: str = Field(min_length=1)
    price_minor: int = Field(ge=0)
    initial_stock: int = Field(ge=0)


class CreateProductRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    image_url: str | None = Field(default=None, max_length=500)
    skus: list[CreateSKURequest] = Field(min_length=1)
